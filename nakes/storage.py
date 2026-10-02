import os
import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabaseStorage(Storage):
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or getattr(settings, 'SUPABASE_BUCKET', 'sim-ktkl-files')
        self.supabase_url = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
        self.supabase_key = getattr(settings, 'SUPABASE_KEY', '')

    def _get_headers(self, content_type='application/octet-stream'):
        return {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': content_type,
            'x-upsert': 'true',
        }

    def _save(self, name, content):
        name = name.replace('\\', '/')
        if not self.supabase_url or not self.supabase_key:
            return name

        content.seek(0)
        data = content.read()
        content_type = getattr(content, 'content_type', 'application/octet-stream')

        endpoint = f'{self.supabase_url}/storage/v1/object/{self.bucket_name}/{name}'
        res = requests.post(
            endpoint,
            headers=self._get_headers(content_type),
            data=data,
            timeout=30
        )
        if res.status_code not in (200, 201):
            raise IOError(f'Failed to upload to Supabase: {res.status_code} {res.text}')
        return name

    def _open(self, name, mode='rb'):
        name = name.replace('\\', '/')
        url = self.url(name)
        res = requests.get(url, timeout=30)
        if res.status_code == 200:
            f = ContentFile(res.content)
            f.name = os.path.basename(name)
            return f
        raise FileNotFoundError(f'File {name} not found in Supabase Storage ({res.status_code})')

    def exists(self, name):
        name = name.replace('\\', '/')
        if not self.supabase_url or not self.supabase_key:
            return False
        url = self.url(name)
        res = requests.head(url, timeout=10)
        return res.status_code == 200

    def url(self, name):
        name = name.replace('\\', '/')
        return f'{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{name}'

    def delete(self, name):
        name = name.replace('\\', '/')
        if not self.supabase_url or not self.supabase_key:
            return
        endpoint = f'{self.supabase_url}/storage/v1/object/{self.bucket_name}/{name}'
        requests.delete(endpoint, headers=self._get_headers(), timeout=15)

    def size(self, name):
        name = name.replace('\\', '/')
        url = self.url(name)
        res = requests.head(url, timeout=10)
        if res.status_code == 200:
            return int(res.headers.get('Content-Length', 0))
        return 0
