from http import HTTPStatus

from django.contrib import auth
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post, User

USERNAME_NOT_AUTH = 'not_author'
USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'
USERNAME_FOLLOWER = 'follower'

INDEX_URL = reverse('posts:index')
POST_CREATE_URL = reverse('posts:post_create')
GROUP_URL = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE_URL = reverse('posts:profile', args=[USERNAME_AUTHOR])
LOGIN_URL = reverse('users:login')
LOGIN_URL_CREATE = f'{LOGIN_URL}?next={POST_CREATE_URL}'
FOLLOW_INDEX_URL = reverse('posts:follow_index')
PROFILE_FOLLOW_URL = reverse('posts:profile_follow', args=[USERNAME_AUTHOR])
PROFILE_UNFOLLOW_URL = reverse('posts:profile_unfollow',
                               args=[USERNAME_AUTHOR])
LOGIN_FOLLOW_INDEX_URL = f'{LOGIN_URL}?next={FOLLOW_INDEX_URL}'
LOGIN_PROFILE_FOLLOW_URL = f'{LOGIN_URL}?next={PROFILE_FOLLOW_URL}'
LOGIN_PROFILE_UNFOLLOW_URL = f'{LOGIN_URL}?next={PROFILE_UNFOLLOW_URL}'
BAD_PAGE_URL = '/badpage-test'

OK = HTTPStatus.OK
FOUND = HTTPStatus.FOUND
NOT_FOUND = HTTPStatus.NOT_FOUND


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME_AUTHOR)
        cls.user_not_author = User.objects.create(username=USERNAME_NOT_AUTH)
        cls.user_follower = User.objects.create(username=USERNAME_FOLLOWER)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=GROUP_SLUG,
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='a' * 20,
        )
        cls.follow = Follow.objects.create(
            user=cls.user_follower,
            author=cls.user,
        )
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.LOGIN_URL_EDIT = f'{LOGIN_URL}?next={cls.POST_EDIT_URL}'
        cls.guest = Client()
        cls.author = Client()
        cls.author.force_login(cls.user)
        cls.another = Client()
        cls.another.force_login(cls.user_not_author)
        cls.follower = Client()
        cls.follower.force_login(cls.user_follower)

    def setUp(self):
        cache.clear()

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""
        cases = {
            INDEX_URL: 'posts/index.html',
            GROUP_URL: 'posts/group_list.html',
            PROFILE_URL: 'posts/profile.html',
            self.POST_DETAIL_URL: 'posts/post_detail.html',
            self.POST_EDIT_URL: 'posts/create_post.html',
            POST_CREATE_URL: 'posts/create_post.html',
            FOLLOW_INDEX_URL: 'posts/follow.html',
            BAD_PAGE_URL: 'core/404.html'
        }
        for url, template in cases.items():
            with self.subTest(url=url):
                self.assertTemplateUsed(
                    self.author.get(url), template)

    def test_status_code(self):
        """Проверка status_code для пользователей"""
        cases = [
            [BAD_PAGE_URL, self.author, NOT_FOUND],
            [FOLLOW_INDEX_URL, self.another, OK],
            [FOLLOW_INDEX_URL, self.guest, FOUND],
            [GROUP_URL, self.guest, OK],
            [INDEX_URL, self.guest, OK],
            [POST_CREATE_URL, self.another, OK],
            [POST_CREATE_URL, self.guest, FOUND],
            [PROFILE_FOLLOW_URL, self.another, FOUND],
            [PROFILE_FOLLOW_URL, self.author, FOUND],
            [PROFILE_FOLLOW_URL, self.guest, FOUND],
            [PROFILE_UNFOLLOW_URL, self.author, NOT_FOUND],
            [PROFILE_UNFOLLOW_URL, self.follower, FOUND],
            [PROFILE_UNFOLLOW_URL, self.guest, FOUND],
            [PROFILE_URL, self.guest, OK],
            [self.POST_DETAIL_URL, self.guest, OK],
            [self.POST_EDIT_URL, self.another, FOUND],
            [self.POST_EDIT_URL, self.author, OK],
            [self.POST_EDIT_URL, self.guest, FOUND],
        ]
        for url, client, expected in cases:
            with self.subTest(
                url=url,
                client=auth.get_user(client).username,
                expected=expected
            ):
                self.assertEqual(client.get(url).status_code, expected)

    def test_redirect(self):
        """Проверка редиректа для пользователей."""
        cases = [
            [POST_CREATE_URL, self.guest, LOGIN_URL_CREATE],
            [self.POST_EDIT_URL, self.another, self.POST_DETAIL_URL],
            [self.POST_EDIT_URL, self.guest, self.LOGIN_URL_EDIT],
            [FOLLOW_INDEX_URL, self.guest, LOGIN_FOLLOW_INDEX_URL],
            [PROFILE_FOLLOW_URL, self.guest, LOGIN_PROFILE_FOLLOW_URL],
            [PROFILE_UNFOLLOW_URL, self.guest, LOGIN_PROFILE_UNFOLLOW_URL],
            [PROFILE_FOLLOW_URL, self.another, PROFILE_URL],
            [PROFILE_UNFOLLOW_URL, self.follower, PROFILE_URL],
            [PROFILE_FOLLOW_URL, self.author, PROFILE_URL]
        ]
        for url, client, expected in cases:
            with self.subTest(
                url=url,
                client=auth.get_user(client).username,
                expected=expected
            ):
                self.assertRedirects(client.get(url), expected)
