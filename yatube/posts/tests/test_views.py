import shutil
import tempfile

from django.contrib import auth
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
PROFILE_FOLLOW_URL = reverse('posts:profile_follow', args=[USERNAME_AUTHOR])
PROFILE_UNFOLLOW_URL = reverse('posts:profile_unfollow',
                               args=[USERNAME_AUTHOR])

RESULT_FOR_SECOND_PAGE = 1

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME_AUTH)
        cls.author = User.objects.create(username=USERNAME_AUTHOR)
        cls.user_2 = User.objects.create(username=USERNAME_USER_2)
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
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.guest = Client()
        cls.another = Client()
        cls.another.force_login(cls.user)
        cls.another_2 = Client()
        cls.another_2.force_login(cls.user_2)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def test_pages_show_correct_context(self):
        """Страницы index, group_list, profile, post_detail
            с правильным контекстом.
        """
        context_objects = {
            INDEX_URL: 'page_obj',
            GROUP_URL: 'page_obj',
            PROFILE_URL: 'page_obj',
            FOLLOW_INDEX_URL: 'page_obj',
            self.POST_DETAIL_URL: 'post'
        }
        for url, context_var in context_objects.items():
            response = self.another.get(url)
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

    def test_post_in_mistake_page(self):
        """Пост не попал на чужую ленты."""
        cases = {
            self.authorized_client: GROUP_URL_2,
            self.another_2: FOLLOW_INDEX_URL
        }
        for client, url in cases.items():
            with self.subTest(
                    url=url,
                    client=auth.get_user(client).username):
                self.assertNotIn(
                    self.post,
                    client.get(url).context["page_obj"]
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
        """Запись появляется в ленте тех, кто подписан."""
        self.assertIn(
            self.post,
            self.another.get(FOLLOW_INDEX_URL).context["page_obj"]
        )

    def test_cache_index_page(self):
        """Проверка работы кеша"""
        content_before = self.another.get(INDEX_URL).content
        Post.objects.create(
            text='Проверка кэша.',
            author=self.user
        )
        content_after = self.authorized_client.get(INDEX_URL).content
        self.assertEqual(content_before, content_after)
        cache.clear()
        content_after_cache_clear = self.authorized_client.get(INDEX_URL)
        self.assertNotEqual(content_before, content_after_cache_clear)

    def test_unauthorized_comments(self):
        """Проверка базы после запросов подписаться и отписаться."""
        follows = set(Follow.objects.all())
        self.another_2.post(PROFILE_FOLLOW_URL)
        follows = set(Follow.objects.all()) - follows
        self.assertEqual(len(follows), 1)
        follow = follows.pop()
        self.assertEqual(follow.author_id, self.author.id)
        self.assertEqual(follow.user_id, self.user_2.id)
        self.another_2.post(PROFILE_UNFOLLOW_URL)
        self.assertNotIn(follow, set(Follow.objects.all()))


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username=USERNAME_AUTHOR)
        cls.user = User.objects.create(username=USERNAME_AUTH)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=GROUP_SLUG,
            description='Тестовое описание',
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author
        )
        Post.objects.bulk_create(
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group) for i in range(
                settings.NUM_POSTS_PER_PAGE + RESULT_FOR_SECOND_PAGE)
        )
        cls.another = Client()
        cls.another.force_login(cls.user)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)

    def setUp(self):
        cache.clear()

    def test_paginator(self):
        urls = {
            INDEX_URL: settings.NUM_POSTS_PER_PAGE,
            INDEX_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
            GROUP_URL: settings.NUM_POSTS_PER_PAGE,
            GROUP_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
            PROFILE_URL: settings.NUM_POSTS_PER_PAGE,
            PROFILE_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
            FOLLOW_INDEX_URL + '?page=2': RESULT_FOR_SECOND_PAGE,
        }
        for url, count in urls.items():
            self.assertEqual(
                len(self.another.get(url).context['page_obj']),
                count)
