import datetime
import hashlib

from django.core import mail
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from login import models, form
from logsite import settings


def index(request):
    pass
    return render(request, template_name='login/index.html')


# 登录
@csrf_exempt
def login(request):
    if request.session.get('is_login', None):
        return redirect('index')
    if request.method == 'POST':
        login_form = form.UserForm(request.POST)
        if login_form.is_valid():
            name = login_form.cleaned_data['name']
            password = login_form.cleaned_data['password']
            try:
                user = models.User.objects.get(name=name)
                # 判断是否邮件验证
                if user.has_confirm == False:
                    message = "该用户还未通过邮件确认！"
                    return render(request, 'login/login.html', locals())
                if user.password == hashlib.sha1(password.encode()).hexdigest():
                    # print(name, password)
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    request.session.set_expiry(0)
                    message = '登录成功！'
                    return render(request, 'login/index.html', context={'message': message})
                else:
                    message = '密码错误！'
                    return render(request, 'login/login.html', context={'message': message, 'login_form': login_form})
            except:
                message = '该用户不存在！'
                return render(request, 'login/login.html', context={'message': message, 'login_form': login_form})

    login_form = form.UserForm()
    return render(request, 'login/login.html', context={'login_form': login_form})


# 注册
def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hashlib.sha1((user.name + now).encode()).hexdigest()
    models.ConfirmString.objects.create(code=code, user=user)
    return code


def sendmail(to_mail, code):
    subject = '来自汪春旺网站的注册确认邮件'
    body = '感谢注册，http://www.cnblogs.com/wcwnina2018/，这里是汪春旺的博客和教程站点，' \
           '专注于Python和Django技术的分享！你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'
    html_content = '<p>感谢注册，<a href="http://{0}/confirm/?code={1}" target=blank>http://www.cnblogs.com/wcwnina2018/</a>，' \
                   '这里是汪春旺的博客和教程站点，专注于Python和Django技术的分享！</p>' \
                   '<p>请点击站点链接完成注册确认！此链接有效期为{2}天！</p>'.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)

    msg = mail.EmailMultiAlternatives(subject=subject, body=body, from_email=settings.EMAIL_HOST_USER, to=[to_mail, ])
    msg.attach_alternative(content=html_content, mimetype='text/html')
    msg.send()


def register(request):
    if request.session.get('is_login', None):
        return redirect('index')
    if request.method == "POST":
        register_form = form.RegisterForm(request.POST)
        if register_form.is_valid():  # 获取数据
            name = register_form.cleaned_data['name']
            password1 = register_form.cleaned_data['password1']
            password2 = register_form.cleaned_data['password2']
            email = register_form.cleaned_data['email']
            sex = register_form.cleaned_data['sex']
            if password1 != password2:  # 判断两次密码是否相同
                message = "两次输入的密码不同！"
                return render(request, 'login/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=name)
                if same_name_user:  # 用户名唯一
                    message = '用户已经存在，请重新选择用户名！'
                    return render(request, 'login/register.html', locals())
                same_email_user = models.User.objects.filter(email=email)
                if same_email_user:  # 邮箱地址唯一
                    message = '该邮箱地址已被注册，请使用别的邮箱！'
                    return render(request, 'login/register.html', locals())

            # 当一切都OK的情况下，创建新用户
            new_user = models.User.objects.create()
            new_user.name = name
            new_user.password = hashlib.sha1(password1.encode()).hexdigest()
            new_user.email = email
            new_user.sex = sex
            new_user.save()

            # 邮箱验证
            code = make_confirm_string(user=new_user)
            sendmail(to_mail=email, code=code)
            message = '请前往注册邮箱，进行邮件确认！'
            return render(request, 'login/confirm.html', locals())  # 跳转到等待邮件确认页面。
    register_form = form.RegisterForm()
    return render(request, 'login/register.html', locals())


# 邮件验证
def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)
    except:
        message = '无效的邮件验证码！'
        return render(request, 'login/confirm.html', locals())
    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(days=settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '您的邮件验证码已过期，请重新注册。'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirm = True
        confirm.user.save()
        confirm.delete()
        message = '恭喜，验证成功！请前往登录。'
        return render(request, 'login/confirm.html', locals())


# 退出
def logout(request):
    if not request.session.get('is_login', None):
        return redirect('index')
    request.session.flush()
    return redirect("/index/")
