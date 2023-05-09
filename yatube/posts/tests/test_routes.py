from django.test import TestCase
from django.urls import reverse


USERNAME_AUTHOR = 'author'
GROUP_SLUG = 'group_1'
POST_ID = 1

URL_NAMES = [
    ['/', 'index'],
    ['/follow/', 'follow_index'],
    [f'/group/{GROUP_SLUG}/', 'group_list', GROUP_SLUG],
    [f'/profile/{USERNAME_AUTHOR}/', 'profile', USERNAME_AUTHOR],
    ['/create/', 'post_create'],
    [f'/posts/{POST_ID}/', 'post_detail', POST_ID],
    [f'/posts/{POST_ID}/edit/', 'post_edit', POST_ID],
    [f'/posts/{POST_ID}/comment/', 'add_comment', POST_ID],
    [f'/profile/{USERNAME_AUTHOR}/follow/', 'profile_follow', USERNAME_AUTHOR],
    [f'/profile/{USERNAME_AUTHOR}/unfollow/',
     'profile_unfollow', USERNAME_AUTHOR],
]


class PostURLTests(TestCase):
    def test_urls_names(self):
        """Расчеты name дают ожидаемые URL"""
        for url, name, *args in URL_NAMES:
            with self.subTest():
                self.assertEqual(url, reverse(f'posts:{name}', args=args))
