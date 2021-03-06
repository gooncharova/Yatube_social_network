import tempfile
import time

from django.shortcuts import reverse
from django.test import Client, TestCase, override_settings

from PIL import Image

from .models import Follow, Group, Post, User

DUMMY_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}


class Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="TestUser", password="Qwerty")
        self.post = Post.objects.create(
            text="Проверка работы", author=self.user)

    def test_creature_profile(self):
        response = self.client.get(reverse("profile", kwargs={
            "username": self.user}), follow=True)
        self.assertEqual(response.status_code, 200, msg="Профиль не создан!")

    def test_creature_new_post(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("post", kwargs={"username": self.user,
                                    "post_id": self.post.pk}))
        self.assertEqual(response.status_code, 200, msg="Пост не создан!")

    def test_not_auth_user_new_post(self):
        response = self.client.get(reverse("new_post"), follow=True)
        self.assertRedirects(response, "/auth/login/?next=/new/",
                             msg_prefix="Неавторизованный пользователь "
                             "не перенаправлен на страницу входа!")

    @override_settings(CACHES=DUMMY_CACHE)
    def test_new_post_is_exist(self):
        responses = [
            self.client.get(reverse("index")),
            self.client.get(
                reverse("profile", kwargs={"username": self.user})),
            self.client.get(reverse("post", kwargs={"username": self.user,
                                                    "post_id": self.post.pk}))
        ]
        for response in responses:
            self.assertContains(
                response, self.post, msg_prefix="Где-то пост отсутствует...")

    @override_settings(CACHES=DUMMY_CACHE)
    def test_user_can_edit_post(self):
        self.client.force_login(self.user)
        self.client.post(reverse("post_edit", kwargs={
                         "username": self.user, "post_id": self.post.pk}),
                         {"text": "Пост изменен"})
        self.post.text = "Пост изменен"
        self.post.save()
        responses = [
            self.client.get(reverse("index")),
            self.client.get(
                reverse("profile", kwargs={"username": self.user})),
            self.client.get(reverse("post", kwargs={"username": self.user,
                                                    "post_id": self.post.pk}))
        ]
        for response in responses:
            self.assertContains(
                response, self.post, msg_prefix="Пост не отредактирован или "
                "отображается не везде!")

    def test_return_404(self):
        response = self.client.get("/page_not_exist/")
        self.assertEqual(response.status_code, 404, msg="Сервер возвращает "
                         "другой код!")


class TestImage(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="TestUser", password="Qwerty")
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title="TestGroup", slug="Test_Group")
        self.post = Post.objects.create(
            text="Проверка изображений", author=self.user)
        post_edit_data = reverse("post_edit", kwargs={
            "username": self.user, "post_id": self.post.pk})
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image = Image.new("RGB", (200, 200), "white")
            image.save(f, "PNG")
            self.image = open(f.name, mode="rb")
            self.client.post(post_edit_data,
                             {"author": self.user,
                              "text": "Прикрепляем изображение",
                              "image": self.image,
                              "group": self.group.pk})

    def test_post_has_image(self):
        response = self.client.get(reverse("post",
                                           kwargs={"username": self.user,
                                                   "post_id": self.post.pk}))
        self.assertContains(response, "img class=", status_code=200,
                            msg_prefix="На странице нет тега <img>!")

    @override_settings(CACHES=DUMMY_CACHE)
    def test_image_is_exist(self):
        responses = [
            self.client.get(reverse("index")),
            self.client.get(
                reverse("profile", kwargs={"username": self.user})),
            self.client.get(
                reverse("group", kwargs={"slug": self.group.slug}))
        ]
        for response in responses:
            self.assertContains(
                response, "img class=", status_code=200, msg_prefix="Картинка "
                "отображается не везде!")

    def test_not_image_protection(self):
        post_edit_data = reverse("post_edit", kwargs={
            "username": self.user, "post_id": self.post.pk})
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Test text")
            self.not_image = open(f.name, "rb")
            response = self.client.post(post_edit_data,
                                        {"author": self.user,
                                         "text": "Прикрепляем не изображение",
                                         "image": self.not_image})
        self.assertFormError(response, "form", "image",
                             "Загрузите правильное изображение. Файл, который "
                             "вы загрузили, поврежден или не является "
                             "изображением.", msg_prefix="Защита от не-"
                             "картинок не работает!")

    def tearDown(self):
        self.image.close()
        self.not_image.close()


class TestCache(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="TestUser", password="Qwerty")
        self.post = Post.objects.create(
            text="Проверка кэша", author=self.user)
        self.client.force_login(self.user)

    def test_cache_post_is_absent(self):
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, "Проверка кэша",
                               msg_prefix="Пост отобразился раньше, чем нужно")

    def test_cache_post_is_present(self):
        time.sleep(20)
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Проверка кэша",
                            msg_prefix="Пост не отобразился!")


class TestFollow(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="TestUser", password="Qwerty")
        self.author = User.objects.create_user(
            username="TestAuthor", password="Qwerty2")

    def test_not_auth_follow(self):
        response = self.client.get(
            reverse("profile_follow", kwargs={"username": self.author}),
            follow=True)
        self.assertRedirects(response, "/auth/login/?next=/TestAuthor/follow/",
                             msg_prefix="Неавторизованный пользователь "
                             "имеет возможность подписки!")

    def test_auth_follow(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("profile_follow", kwargs={"username": self.user}),
            follow=True)
        self.assertRedirects(response, "/follow/",
                             msg_prefix="Авторизованному пользователю "
                             "недоступна подписка!")

    def test_auth_unfollow(self):
        self.client.force_login(self.user)
        self.client.get(
            reverse("profile_follow", kwargs={"username": self.user}),
            follow=True)
        response = self.client.get(
            reverse("profile_unfollow", kwargs={"username": self.user}),
            follow=True)
        self.assertRedirects(response, "/follow/",
                             msg_prefix="Авторизованному пользователю "
                             "недоступна отписка!")

    def test_new_post_follow(self):
        self.post = Post.objects.create(
            text="Проверка подписок", author=self.author)
        self.client.force_login(self.user)
        response = self.client.get(reverse("follow_index"), follow=True)
        self.assertNotContains(response, "Проверка подписок",
                               msg_prefix="На странице подписок найден пост "
                               "автора, на которого не подписан пользователь")
        self.follow = Follow.objects.create(
            user=self.user, author=self.author)
        response = self.client.get(reverse("follow_index"), follow=True)
        self.assertContains(response, "Проверка подписок",
                            msg_prefix="На странице подписок не найден пост "
                            "автора, на которого подписан пользователь")


class TestComments(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="TestUser", password="Qwerty")
        self.post = Post.objects.create(
            text="Проверка комментариев", author=self.user)

    def test_only_auth_user_can_comments(self):
        response = self.client.get(
            reverse("add_comment", kwargs={"username": self.user,
                                           "post_id": self.post.pk}))
        self.assertRedirects(response,
                             "/auth/login/?next=/TestUser/1/comment/",
                             msg_prefix="Неавторизованный пользователь "
                             "имеет возможность подписки!")
        self.client.force_login(self.user)
        self.client.post(reverse("add_comment", kwargs={
                         "username": self.user, "post_id": self.post.pk}),
                         {"text": "Проверка комментария"})
        response = self.client.get(
            reverse("post", kwargs={"username": self.user,
                                    "post_id": self.post.pk}))
        self.assertContains(response, "Проверка комментария",
                            msg_prefix="На странице поста не найден "
                            "комментарий!")
