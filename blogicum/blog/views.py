from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from blog.models import Category, Post
from .forms import CommentForm, PostForm
from .models import Comment


def filter_posts():
    return Post.objects.filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True,
    ).annotate(comment_count=Count('comments'))


def index(request):
    page_obj = Paginator(filter_posts().order_by('-pub_date'), 10).get_page(
        request.GET.get('page')
    )
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    page_obj = Paginator(
        filter_posts().filter(category=category).order_by('-pub_date'), 10
    ).get_page(request.GET.get('page'))
    context = {'category': category, 'page_obj': page_obj}
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    posts = filter_posts()
    if request.user.is_authenticated:
        posts = Post.objects.annotate(comment_count=Count('comments')).filter(
            Q(pk=post_id, pub_date__lte=timezone.now(), is_published=True,
                     category__is_published=True)
            | Q(pk=post_id, author=request.user)
        )
    post = get_object_or_404(posts, pk=post_id)
    return render(request, 'blog/detail.html', {
        'post': post, 'comments': post.comments.select_related('author'),
        'form': CommentForm(),
    })


def profile(request, username):
    profile_user = get_object_or_404(get_user_model(), username=username)
    posts = profile_user.posts.all()
    if request.user != profile_user:
        posts = posts.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
    posts = posts.annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'blog/profile.html', {
        'profile': profile_user, 'page_obj': page_obj,
    })


def registration(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'registration/registration_form.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = PostForm(instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    accessible_posts = filter_posts()
    if request.user.is_authenticated:
        accessible_posts = Post.objects.annotate(
            comment_count=Count('comments')
        ).filter(
            Q(
                pk=post_id,
                pub_date__lte=timezone.now(),
                is_published=True,
                category__is_published=True,
            )
            | Q(pk=post_id, author=request.user)
        )
    post = get_object_or_404(accessible_posts, pk=post_id)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/detail.html', {
        'post': post, 'comments': post.comments.select_related('author'),
        'form': form,
    })


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    form = CommentForm(request.POST or None, instance=comment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post.pk)
    return render(request, 'blog/comment.html', {'comment': comment})


@login_required
def edit_profile(request):
    class ProfileForm(forms.ModelForm):
        class Meta:
            model = get_user_model()
            fields = ('first_name', 'last_name', 'username', 'email')

    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/edit_profile.html', {'form': form})
