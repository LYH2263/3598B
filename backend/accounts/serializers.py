from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import Profile
from accounts.services.auth_service import AuthService
from accounts.services.captcha_service import CaptchaService
from accounts.services.reset_service import PasswordResetService
from billing.models import Wallet


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('role', 'student_id', 'phone', 'security_question')


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'is_active', 'profile')


class RegisterSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Profile.ROLE_CHOICES)
    username = serializers.CharField(max_length=150)
    student_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    security_question = serializers.CharField(max_length=255)
    security_answer = serializers.CharField(max_length=255, write_only=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    captcha_id = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=16)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次密码输入不一致。'})

        validate_password(attrs['password'])

        if not CaptchaService.verify_challenge(attrs['captcha_id'], attrs['captcha_answer']):
            raise serializers.ValidationError({'captcha_answer': '验证码错误或已过期。'})

        role = attrs['role']
        student_id = attrs.get('student_id', '').strip()
        phone = attrs.get('phone', '').strip()
        email = attrs.get('email', '').strip()
        username = attrs['username'].strip()
        security_question = attrs.get('security_question', '').strip()
        security_answer = attrs.get('security_answer', '').strip()

        if role == Profile.ROLE_STUDENT and not student_id:
            raise serializers.ValidationError({'student_id': '学生注册必须填写学号。'})

        if not phone and not email:
            raise serializers.ValidationError({'phone': '手机号和邮箱至少填写一项。'})

        if not security_question:
            raise serializers.ValidationError({'security_question': '请输入安全问题。'})

        if len(security_answer) < 2:
            raise serializers.ValidationError({'security_answer': '安全问题答案至少 2 个字符。'})

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': '用户名已存在。'})

        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': '邮箱已被使用。'})

        if student_id and Profile.objects.filter(student_id=student_id).exists():
            raise serializers.ValidationError({'student_id': '学号已存在。'})

        if phone and Profile.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({'phone': '手机号已存在。'})

        attrs['username'] = username
        attrs['student_id'] = student_id or None
        attrs['phone'] = phone or None
        attrs['email'] = email
        attrs['security_question'] = security_question
        attrs['security_answer'] = security_answer
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data['username'],
        )
        profile = Profile.objects.create(
            user=user,
            role=validated_data['role'],
            student_id=validated_data.get('student_id'),
            phone=validated_data.get('phone'),
            security_question=validated_data['security_question'],
        )
        profile.set_security_answer(validated_data['security_answer'])
        profile.save(update_fields=['security_answer_hash'])
        Wallet.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    account = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)
    captcha_id = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=16)

    def validate(self, attrs):
        if not CaptchaService.verify_challenge(attrs['captcha_id'], attrs['captcha_answer']):
            raise serializers.ValidationError({'captcha_answer': '验证码错误或已过期。'})

        user = AuthService.find_user_by_account(attrs['account'])
        if not user or not user.check_password(attrs['password']):
            raise serializers.ValidationError({'account': '账号或密码错误。'})

        attrs['user'] = user
        return attrs


class ResetEmailCodeRequestSerializer(serializers.Serializer):
    account = serializers.CharField(max_length=150)
    security_answer = serializers.CharField(max_length=255)
    captcha_id = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=16)

    def validate(self, attrs):
        if not CaptchaService.verify_challenge(attrs['captcha_id'], attrs['captcha_answer']):
            raise serializers.ValidationError({'captcha_answer': '验证码错误或已过期。'})

        user = AuthService.find_user_by_account(attrs['account'])
        if not user:
            raise serializers.ValidationError({'account': '账号不存在。'})

        profile = getattr(user, 'profile', None)
        if not profile or not profile.check_security_answer(attrs['security_answer']):
            raise serializers.ValidationError({'security_answer': '安全问题答案错误。'})

        if not user.email:
            raise serializers.ValidationError({'account': '该账号未绑定邮箱，无法进行邮箱验证。'})

        attrs['user'] = user
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    account = serializers.CharField(max_length=150)
    security_answer = serializers.CharField(max_length=255)
    email_code = serializers.CharField(max_length=16)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    captcha_id = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=16)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次密码输入不一致。'})

        validate_password(attrs['new_password'])

        if not CaptchaService.verify_challenge(attrs['captcha_id'], attrs['captcha_answer']):
            raise serializers.ValidationError({'captcha_answer': '验证码错误或已过期。'})

        user = AuthService.find_user_by_account(attrs['account'])
        if not user:
            raise serializers.ValidationError({'account': '账号不存在。'})

        profile = getattr(user, 'profile', None)
        if not profile or not profile.check_security_answer(attrs['security_answer']):
            raise serializers.ValidationError({'security_answer': '安全问题答案错误。'})

        if not PasswordResetService.verify_email_code(user, attrs['email_code']):
            raise serializers.ValidationError({'email_code': '邮箱验证码错误或已过期。'})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    balance = serializers.SerializerMethodField()
    wallet_frozen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_active',
            'date_joined',
            'profile',
            'balance',
            'wallet_frozen',
        )

    def get_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.balance if wallet else 0

    def get_wallet_frozen(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return wallet.is_frozen if wallet else False


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Profile.ROLE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('至少提供一个更新字段。')
        return attrs

    def update(self, instance, validated_data):
        role = validated_data.get('role')
        is_active = validated_data.get('is_active')

        if role:
            profile = getattr(instance, 'profile', None)
            if profile:
                profile.role = role
                profile.save(update_fields=['role'])

        if is_active is not None:
            instance.is_active = is_active
            instance.save(update_fields=['is_active'])

        return instance
