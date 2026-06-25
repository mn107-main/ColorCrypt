import os
import io
import json

HAS_S3 = False
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    HAS_S3 = True
except ImportError:
    pass

HAS_FTP = False
try:
    from ftplib import FTP, FTP_TLS
    HAS_FTP = True
except ImportError:
    pass

HAS_GDRIVE = False
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    HAS_GDRIVE = True
except ImportError:
    pass

SCOPES = ['https://www.googleapis.com/auth/drive.file']
GDRIVE_TOKEN_FILE = 'gdrive_token.json'
GDRIVE_CREDS_FILE = 'gdrive_credentials.json'

CLOUD_PROVIDERS = []
if HAS_S3:
    CLOUD_PROVIDERS.append('S3')
if HAS_FTP:
    CLOUD_PROVIDERS.append('FTP')
if HAS_GDRIVE:
    CLOUD_PROVIDERS.append('Google Drive')


class CloudIO:
    def __init__(self, debug_callback=None, progress_callback=None):
        self.debug_callback = debug_callback
        self.progress_callback = progress_callback
        self.ftp_conn = None
        self.gdrive_service = None

    def _log(self, msg):
        if self.debug_callback:
            self.debug_callback(msg)

    def _progress(self, cur, total, msg=''):
        if self.progress_callback:
            self.progress_callback(cur, total, msg)

    def upload(self, provider, local_path, remote_path=None, **kwargs):
        if provider == 'S3':
            return self._upload_s3(local_path, remote_path, **kwargs)
        elif provider == 'FTP':
            return self._upload_ftp(local_path, remote_path, **kwargs)
        elif provider == 'Google Drive':
            return self._upload_gdrive(local_path, remote_path, **kwargs)
        return {'success': False, 'error': f'Неизвестный провайдер: {provider}'}

    def download(self, provider, remote_path, local_path=None, **kwargs):
        if provider == 'S3':
            return self._download_s3(remote_path, local_path, **kwargs)
        elif provider == 'FTP':
            return self._download_ftp(remote_path, local_path, **kwargs)
        elif provider == 'Google Drive':
            return self._download_gdrive(remote_path, local_path, **kwargs)
        return {'success': False, 'error': f'Неизвестный провайдер: {provider}'}

    def _upload_s3(self, local_path, remote_path=None, bucket='colorcrypt', access_key=None, secret_key=None, region='us-east-1'):
        if not HAS_S3:
            return {'success': False, 'error': 'Установите boto3: pip install boto3'}
        try:
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            s3 = session.client('s3')
            if remote_path is None:
                remote_path = os.path.basename(local_path)
            file_size = os.path.getsize(local_path)
            self._log(f"S3 загрузка: {local_path} -> s3://{bucket}/{remote_path}\n")
            s3.upload_file(
                local_path, bucket, remote_path,
                Callback=lambda bytes_transferred: self._progress(
                    bytes_transferred, file_size, f"S3 загрузка... {bytes_transferred}/{file_size}"
                )
            )
            url = f"s3://{bucket}/{remote_path}"
            return {'success': True, 'url': url, 'provider': 'S3', 'path': remote_path, 'bucket': bucket}
        except NoCredentialsError:
            return {'success': False, 'error': 'S3: не указаны credentials'}
        except ClientError as e:
            return {'success': False, 'error': f'S3 ошибка: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _download_s3(self, remote_path, local_path=None, bucket='colorcrypt', access_key=None, secret_key=None, region='us-east-1'):
        if not HAS_S3:
            return {'success': False, 'error': 'Установите boto3: pip install boto3'}
        try:
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            s3 = session.client('s3')
            if local_path is None:
                local_path = os.path.basename(remote_path)
            self._log(f"S3 загрузка: s3://{bucket}/{remote_path} -> {local_path}\n")
            s3.download_file(bucket, remote_path, local_path)
            return {'success': True, 'local_path': local_path, 'provider': 'S3'}
        except NoCredentialsError:
            return {'success': False, 'error': 'S3: не указаны credentials'}
        except ClientError as e:
            return {'success': False, 'error': f'S3 ошибка: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _upload_ftp(self, local_path, remote_path=None, host='localhost', port=21, user='anonymous', password='', tls=False):
        if not HAS_FTP:
            return {'success': False, 'error': 'Установите ftplib (встроен в Python)'}
        try:
            if tls:
                ftp = FTP_TLS()
            else:
                ftp = FTP()
            ftp.connect(host, port)
            ftp.login(user, password)
            if tls:
                ftp.prot_p()
            if remote_path is None:
                remote_path = os.path.basename(local_path)
            file_size = os.path.getsize(local_path)
            self._log(f"FTP загрузка: {local_path} -> {remote_path}@{host}\n")
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f, 1024,
                               callback=lambda data: self._progress(0, file_size, f"FTP {remote_path}..."))
            ftp.quit()
            url = f"ftp://{user}@{host}/{remote_path}"
            return {'success': True, 'url': url, 'provider': 'FTP', 'host': host}
        except Exception as e:
            return {'success': False, 'error': f'FTP ошибка: {e}'}

    def _download_ftp(self, remote_path, local_path=None, host='localhost', port=21, user='anonymous', password='', tls=False):
        if not HAS_FTP:
            return {'success': False, 'error': 'Установите ftplib (встроен в Python)'}
        try:
            if tls:
                ftp = FTP_TLS()
            else:
                ftp = FTP()
            ftp.connect(host, port)
            ftp.login(user, password)
            if tls:
                ftp.prot_p()
            if local_path is None:
                local_path = os.path.basename(remote_path)
            self._log(f"FTP загрузка: {remote_path}@{host} -> {local_path}\n")
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
            ftp.quit()
            return {'success': True, 'local_path': local_path, 'provider': 'FTP'}
        except Exception as e:
            return {'success': False, 'error': f'FTP ошибка: {e}'}

    def _get_gdrive_service(self):
        if self.gdrive_service:
            return self.gdrive_service
        if not HAS_GDRIVE:
            return None
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        import pickle

        creds = None
        if os.path.exists(GDRIVE_TOKEN_FILE):
            with open(GDRIVE_TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(GDRIVE_CREDS_FILE):
                    self._log("Google Drive: файл credentials не найден. Создайте gdrive_credentials.json\n")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(GDRIVE_CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(GDRIVE_TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        self.gdrive_service = build('drive', 'v3', credentials=creds)
        return self.gdrive_service

    def _upload_gdrive(self, local_path, remote_path=None, folder_id=None):
        service = self._get_gdrive_service()
        if service is None:
            return {'success': False, 'error': 'Google Drive: не настроен'}
        try:
            file_name = remote_path or os.path.basename(local_path)
            media = MediaFileUpload(local_path, resumable=True)
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            self._log(f"Google Drive загрузка: {local_path} -> {file_name}\n")
            request = service.files().create(body=file_metadata, media_body=media, fields='id,name,webViewLink')
            response = request.execute()
            url = response.get('webViewLink', f"https://drive.google.com/file/d/{response['id']}")
            return {'success': True, 'url': url, 'provider': 'Google Drive', 'file_id': response['id']}
        except Exception as e:
            return {'success': False, 'error': f'Google Drive ошибка: {e}'}

    def _download_gdrive(self, remote_path, local_path=None, file_id=None):
        service = self._get_gdrive_service()
        if service is None:
            return {'success': False, 'error': 'Google Drive: не настроен'}
        try:
            fid = file_id
            if fid is None:
                results = service.files().list(
                    q=f"name='{remote_path}'", fields='files(id, name)').execute()
                items = results.get('files', [])
                if not items:
                    return {'success': False, 'error': f'Google Drive: файл {remote_path} не найден'}
                fid = items[0]['id']
            if local_path is None:
                local_path = remote_path or f"gdrive_download_{int(time.time())}"
            self._log(f"Google Drive загрузка: {fid} -> {local_path}\n")
            request = service.files().get_media(fileId=fid)
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        self._progress(int(status.progress() * 100), 100, "GDrive загрузка...")
            return {'success': True, 'local_path': local_path, 'provider': 'Google Drive'}
        except Exception as e:
            return {'success': False, 'error': f'Google Drive ошибка: {e}'}

    def disconnect(self):
        if self.ftp_conn:
            try:
                self.ftp_conn.quit()
            except:
                pass
            self.ftp_conn = None
