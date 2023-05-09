import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

USERNAME_USER_2 = 'user_2'
USERNAME_AUTH = 'auth'
USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'
GROUP_SLUG_2 = 'group_2'

INDEX_URL = reverse('posts:index')
POST_CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_list', args=[GROUP_SLUG])
GROUP_URL_2 = reverse('posts:group_list', args=[GROUP_SLUG_2])
PROFILE_URL = reverse('posts:profile', args=[USERNAME_AUTHOR])
FOLLOW_INDEX_URL = reverse('posts:follow_index')

POST_PATH = 'posts/'

RESULT_FOR_SECOND_PAGE = 1


class PostViewsTests(TestCase):
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
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='a' * 20,
            image=cls.uploaded
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest = Client()
        self.another = Client()
        self.another.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_pages_show_correct_context(self):
        """Страницы index, group_list, profile, post_detail
            с правильным контекстом.
        """
        context_objects = {
            INDEX_URL: 'page_obj',
            GROUP_URL: 'page_obj',
            PROFILE_URL: 'page_obj',
            self.POST_DETAIL_URL: 'post'
        }
        for url, context_var in context_objects.items():
            response = self.guest.get(url)
            context_obj = response.context[context_var]
            if context_var == 'page_obj':
                self.assertEqual(len(context_obj), 1)
                post = context_obj[0]
            else:
                post = context_obj
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group, self.post.group)
            self.assertEqual(post.id, self.post.id)
            self.assertEqual(post.image, self.post.image)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Пост не попал на чужую Групп-ленту."""
        self.assertNotIn(
            self.post,
            self.authorized_client.get(GROUP_URL_2).context["page_obj"]
        )

    def test_context_group_in_group_list(self):
        """Группа в контексте Групп-ленты без искажения атрибутов."""
        group = self.authorized_client.get(GROUP_URL).context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.description, self.group.description)
        self.assertEqual(group.id, self.group.id)

    def test_context_author_profile(self):
        """Автор в контексте Профиля."""
        self.assertEqual(
            self.authorized_client.get(PROFILE_URL).context['author'],
            self.author)

    def test_post_follow(self):
        """Запись не появляется в ленте тех, кто не подписан."""
        self.assertNotIn(
            self.post,
            self.another.get(FOLLOW_INDEX_URL).context["page_obj"]
        )

    def test_cache_index_page(self):
        """Проверка работы кеша"""
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.author)
        content_add = self.authorized_client.get(
            INDEX_URL).content
        post.delete()
        content_delete = self.authorized_client.get(
            INDEX_URL).content
        self.assertEqual(content_add, content_delete)
        cache.clear()
        content_cache_clear = self.authorized_client.get(
            INDEX_URL).content
        self.assertNotEqual(content_add, content_cache_clear)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username=USERNAME_AUTHOR)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=GROUP_SLUG,
            description='Тестовое описание',
        )
        Post.objects.bulk_create(
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group) for i in range(
                settings.NUM_POSTS_PER_PAGE + RESULT_FOR_SECOND_PAGE)
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_paginator(self):
        urls = {
            INDEX_URL: settings.NUM_POSTS_PER_PAGE,
            INDEX_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
            GROUP_URL: settings.NUM_POSTS_PER_PAGE,
            GROUP_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
            PROFILE_URL: settings.NUM_POSTS_PER_PAGE,
            PROFILE_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
        }
        for url, count in urls.items():
            self.assertEqual(
                len(self.authorized_client.get(url).context['page_obj']),
                count)


class FollowViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME_AUTH)
        cls.user_2 = User.objects.create(username=USERNAME_USER_2)
        cls.author = User.objects.create(username=USERNAME_AUTHOR)
        cls.post = Post.objects.create(
            author=cls.author,
            text='a' * 20,
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        Follow.objects.get_or_create(
            user=cls.user,
            author=cls.author
        )

    def setUp(self):
        self.guest = Client()
        self.guest.force_login(self.user_2)
        self.another = Client()
        self.another.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_post_follow(self):
        """Запись не появляется в ленте тех, кто не подписан."""
        self.assertNotIn(
            self.post,
            self.guest.get(FOLLOW_INDEX_URL).context["page_obj"]
        )

    def test_post_follow(self):
        """Запись появляется в ленте тех, кто подписан."""
        self.assertIn(
            self.post,
            self.another.get(FOLLOW_INDEX_URL).context["page_obj"]
        )
