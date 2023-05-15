from django.test import TestCase

from posts.models import Comment, Follow, Group, Post, User


class ModelsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.author = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_1',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='a' * 20,
        )
        cls.comment = Comment.objects.create(
            text='Комментарий для поста',
            author=cls.user,
            post=cls.post,
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author,
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        test_str = {
            self.group: self.group.title,
            self.post: self.post.text[:15],
            str(self.comment): self.comment.text[:15],
            str(self.follow): f'{self.user} подписался на {self.author}'
        }

        for field, expected in test_str.items():
            with self.subTest(class_name=type(self).__name__):
                self.assertEqual(
                    str(field), expected)

    def test_verbose_name(self):
        """verbose_name в полях совпадает с ожидаемым."""
        field_verboses = [
            [Post, 'text', 'Текст записи'],
            [Post, 'pub_date', 'Дата публикации'],
            [Post, 'author', 'Автор'],
            [Post, 'group', 'Группа'],
            [Post, 'image', 'Картинка'],
            [Group, 'title', 'Название'],
            [Group, 'slug', 'Идентификатор'],
            [Group, 'description', 'Описание'],
            [Comment, 'post', 'Запись'],
            [Comment, 'author', 'Автор'],
            [Comment, 'text', 'Текст комментария'],
            [Follow, 'user', 'Подписчик'],
            [Follow, 'author', 'Автор']
        ]
        for model, value, expected in field_verboses:
            with self.subTest(value=value):
                self.assertEqual(
                    model._meta.get_field(value).verbose_name, expected)

    def test_help_text(self):
        """help_text в полях совпадает с ожидаемым."""
        field_help_texts = [
            [Post, 'text', 'Введите текст записи'],
            [Post, 'author', 'Автор этой записи'],
            [Post, 'group', 'Группа, к которой будет относиться запись'],
            [Post, 'image', 'Картинка записи'],
            [Group, 'title', 'Введите название группы'],
            [Group, 'slug', 'Введите идентификатор группы'],
            [Group, 'description', 'Введите описание группы'],
            [Comment, 'post',
             'Запись, к которой будет относиться комментарий'],
            [Comment, 'author', 'Автор этого комментария'],
            [Comment, 'text', 'Введите текст комментария'],
            [Follow, 'user', 'Подписчик'],
            [Follow, 'author', 'Автор']
        ]
        for model, field, expected_value in field_help_texts:
            with self.subTest(field=field):
                self.assertEqual(
                    model._meta.get_field(field).help_text, expected_value)
