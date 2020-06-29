from .base import *

DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = ['ip-address', 'www.your-website.com']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': ''
    }
}

STRIPE_PUBLIC_KEY = config('pk_test_51GGkPGKLvRx6f1cL1ehVtHmpwavR7dE6Csb2qtHaPcmUyoFp3T1PKfzCi3k4LenTZcocOkKcOTgHdOjGreRcgolN004e6F4Ynh')
STRIPE_SECRET_KEY = config('sk_test_51GGkPGKLvRx6f1cLwi7Gbp8JSUofdV6c8tbeYztY6JUvheBxUw8FiXOGXMDtpl7ZNQjLCw011gvxeeghX6NOApMh00yKobozMR')