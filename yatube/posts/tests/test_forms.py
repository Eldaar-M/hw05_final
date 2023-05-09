import shutil
import tempfile

from http import HTTPStatus

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

USERNAME_AUTH = 'auth'
USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'
INDEX_URL = reverse('posts:index')
POST_CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE_URL = reverse('posts:profile', args=[USERNAME_AUTHOR])

POST_PATH = 'posts/'


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
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='a' * 20,
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        self.unauthorized_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

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
        post = set(Post.objects.all()) - posts
        self.assertEqual(len(post), 1)
        post = post.pop()
        self.assertRedirects(response, PROFILE_URL)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.image.name, POST_PATH + form_data['image'].name)
        self.assertEqual(post.author, self.author)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменяем текст',
            'group': self.group.id,
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


class CommentFormTests(TestCase):
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
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='a' * 20,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            text='a' * 20,
            author=cls.author
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.COMMENT_URL = reverse('posts:add_comment', args=[cls.post.id])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

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
        comment = set(Comment.objects.all()) - comments
        self.assertEqual(len(comment), 1)
        comment = comment.pop()
        self.assertRedirects(response, self.POST_DETAIL_URL)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post.id, self.post.id)
        self.assertEqual(comment.author, self.author)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_edit_shows_correct_context(self):
        """Форма add_comments сформирована с правильным контекстом."""
        fields = self.authorized_author.get(
            self.POST_DETAIL_URL).context.get('form').fields
        self.assertIsInstance(fields.get('text'), forms.fields.CharField)

    def test_pages_show_correct_context(self):
        """Комментарии сформированы с правильным контекстом."""
        comments = self.authorized_author.get(
            self.POST_DETAIL_URL).context['page_obj']
        self.assertEqual(len(comments), 1)
        comment = comments[0]
        self.assertEqual(comment.text, self.comment.text)
        self.assertEqual(comment.post.id, self.post.id)
        self.assertEqual(comment.author, self.author)
