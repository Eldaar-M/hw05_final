from http import HTTPStatus

from django.contrib import auth
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

USERNAME_NOT_AUTH = 'not_author'
USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'

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


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME_AUTHOR)
        cls.user_not_author = User.objects.create(username=USERNAME_NOT_AUTH)
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
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.LOGIN_URL_EDIT = f'{LOGIN_URL}?next={cls.POST_EDIT_URL}'
        cls.COMMENT_URL = reverse('posts:add_comment', args=[cls.post.id])
        cls.LOGIN_URL_COMMENT = f'{LOGIN_URL}?next={cls.COMMENT_URL}'

    def setUp(self):
        self.guest = Client()
        self.author = Client()
        self.author.force_login(self.user)
        self.another = Client()
        self.another.force_login(self.user_not_author)
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
        }
        for url, template in cases.items():
            with self.subTest(url=url):
                self.assertTemplateUsed(
                    self.author.get(url), template)

    def test_status_code(self):
        """Проверка status_code для пользователей"""
        cases = [
            [INDEX_URL, self.guest, HTTPStatus.OK],
            [GROUP_URL, self.guest, HTTPStatus.OK],
            [PROFILE_URL, self.guest, HTTPStatus.OK],
            [POST_CREATE_URL, self.guest, HTTPStatus.FOUND],
            [self.POST_EDIT_URL, self.guest, HTTPStatus.FOUND],
            [self.COMMENT_URL, self.guest, HTTPStatus.FOUND],
            [self.POST_DETAIL_URL, self.guest, HTTPStatus.OK],
            [FOLLOW_INDEX_URL, self.guest, HTTPStatus.FOUND],
            [PROFILE_FOLLOW_URL, self.guest, HTTPStatus.FOUND],
            [PROFILE_UNFOLLOW_URL, self.guest, HTTPStatus.FOUND],
            [FOLLOW_INDEX_URL, self.another, HTTPStatus.OK],
            [POST_CREATE_URL, self.another, HTTPStatus.OK],
            [self.POST_EDIT_URL, self.another, HTTPStatus.FOUND],
            [self.POST_EDIT_URL, self.author, HTTPStatus.OK],
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
            [self.COMMENT_URL, self.guest, self.LOGIN_URL_COMMENT]
        ]
        for url, client, expected in cases:
            with self.subTest(
                url=url,
                client=client,
                expected=expected
            ):
                self.assertRedirects(client.get(url), expected)

    def test_for_404_page(self):
        """Запрос к несуществующей странице вернет 404
        и будет использован кастомный шаблон."""
        response = self.guest.get('/badpage-test', follow=True)
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
        )
        self.assertTemplateUsed(response, 'core/404.html')
