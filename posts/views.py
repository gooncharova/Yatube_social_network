from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def index(request):
    post_list = Post.objects.order_by("-pub_date").all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "index.html", {"page": page, "paginator": paginator,
                                          "cache_timeout":
                                          settings.CACHE_TIME})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.group_posts.order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"group": group, "page": page,
                                          "paginator": paginator})


@login_required
def new_post(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            return redirect("index")
    form = PostForm()
    return render(request, "new_post.html", {"form": form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts_author = author.author_posts.order_by("-pub_date")
    paginator = Paginator(posts_author, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    following = None
    if author.following.filter(user=request.user.id):
        following = True
    return render(request, "profile.html", {"author": author, "page": page,
                                            "paginator": paginator,
                                            "following": following})


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author=author, pk=post_id)
    form = CommentForm()
    comments = post.comments_post.order_by("-created")
    return render(request, "post.html", {"author": author, "post": post,
                                         "form": form,
                                         "comments": comments})


@login_required
def post_edit(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author=author, pk=post_id)
    if request.user != author:
        return redirect("post", username=post.author, post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None, instance=post)
    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            return redirect("post", username=post.author, post_id=post.id)
    return render(request, "new_post.html", {"form": form, "post": post,
                                             "edit": True})


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = request.user
            new_comment.post = post
            new_comment.save()
            return redirect("post", username=post.author, post_id=post.id)
    form = CommentForm()
    return redirect("post", username=author.username, post_id=post.id)


@login_required
def follow_index(request):
    following = Follow.objects.all().values("author")
    post_list = Post.objects.filter(author__in=following).order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "follow.html", {"page": page,
                                           "paginator": paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follows_count = Follow.objects.filter(
        user=request.user, author=author).count()
    if request.user != author and follows_count == 0:
        follows = Follow.objects.create(user=request.user, author=author)
        follows.save()
    return redirect("follow_index")


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    following = Follow.objects.filter(user=request.user, author=author)
    following.delete()
    return redirect("follow_index")
