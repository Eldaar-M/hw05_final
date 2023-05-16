import shutil
import tempfile

from http import HTTPStatus


from django import forms
from django.conf import settings
from django.contrib import auth
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

USERNAME_AUTH = 'auth'
USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'
GROUP_SLUG_2 = 'group_2'
INDEX_URL = reverse('posts:index')
POST_CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE_URL = reverse('posts:profile', args=[USERNAME_AUTHOR])
LOGIN_URL = reverse('users:login')

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME_AUTH)
        cls.author = User.objects.create(username=USERNAME_AUTHOR)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=GROUP_SLUG,
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug=GROUP_SLUG_2,
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='a' * 20,
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.uploaded_2 = SimpleUploadedFile(
            name='small_2.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.unauthorized_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)

        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.COMMENT_URL = reverse('posts:add_comment', args=[cls.post.id])
        cls.LOGIN_URL_EDIT = f'{LOGIN_URL}?next={cls.POST_EDIT_URL}'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts = set(Post.objects.all())
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_author.post(
            POST_CREATE_URL,
            data=form_data,
            follow=True
        )
        posts = set(Post.objects.all()) - posts
        self.assertEqual(len(posts), 1)
        post = posts.pop()
        self.assertRedirects(response, PROFILE_URL)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(
            post.image.name,
            settings.IMAGE_PATH + form_data['image'].name
        )
        self.assertEqual(post.author, self.author)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменяем текст',
            'group': self.group_2.id,
            'image': self.uploaded_2
        }
        response = self.authorized_author.post(
            self.POST_EDIT_URL,
            data=form_data,
            follow=True,
        )
        post = Post.objects.get(id=self.post.id)
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(
            post.image.name,
            settings.IMAGE_PATH + form_data['image'].name
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_edit_shows_correct_context(self):
        """Шаблоны post_create, edit сформированы с правильным контекстом."""
        page = [POST_CREATE_URL, self.POST_EDIT_URL]
        FORM_FIELDS = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for url in page:
            fields = self.authorized_author.get(
                url).context.get('form').fields
            for value, expected in FORM_FIELDS.items():
                with self.subTest(value=value):
                    self.assertIsInstance(fields.get(value), expected)

    def test_comments(self):
        """Валидная форма создает запись в Comments."""
        comments = set(Comment.objects.all())
        form_data = {
            'text': 'Тестовый текст',
        }
        response = self.authorized_author.post(
            self.COMMENT_URL,
            data=form_data,
            follow=True
        )
        comments = set(Comment.objects.all()) - comments
        self.assertEqual(len(comments), 1)
        comment = comments.pop()
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.author)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_edit_shows_correct_context(self):
        """Форма add_comments сформирована с правильным контекстом."""
        fields = self.authorized_author.get(
            self.POST_DETAIL_URL).context.get('form').fields
        self.assertIsInstance(fields.get('text'), forms.fields.CharField)

    def test_unauthorized_create_post(self):
        """Неавторизованный клиент не может создать запись в Post."""
        posts = set(Post.objects.all())
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        self.unauthorized_client.post(
            POST_CREATE_URL,
            data=form_data,
            follow=True
        )
        self.assertEqual(len(posts), len(set(Post.objects.all())))

    def test_unauthorized_comments(self):
        """Неавторизованный клиент не может создать запись в Comments."""
        comments = set(Comment.objects.all())
        form_data = {
            'text': 'Тестовый текст',
        }
        self.unauthorized_client.post(
            self.COMMENT_URL,
            data=form_data,
            follow=True
        )
        self.assertEqual(len(comments), len(set(Comment.objects.all())))

    def test_unauthorized_no_author_post_edit(self):
        """Неавторизованный клиент и неавтор
            не могут изменить запись в Post.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменяем текст',
            'group': self.group_2.id,
            'image': self.uploaded_2
        }
        cases = {
            self.unauthorized_client: self.LOGIN_URL_EDIT,
            self.authorized_client: self.POST_DETAIL_URL
        }
        for client, url in cases.items():
            response = client.post(
                self.POST_EDIT_URL,
                data=form_data,
                follow=True,
            )
            post = Post.objects.get(id=self.post.id)
            with self.subTest(client=auth.get_user(client).username):
                self.assertRedirects(response, url)
                self.assertEqual(Post.objects.count(), posts_count)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.image, self.post.image)
