import os
import boto3
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

# AWS S3 클라이언트 초기화
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# 허용된 확장자
ALLOWED_EXTENSIONS = {'zip'}

# 파일 확장자 확인 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """S3에서 파일 목록을 가져와 렌더링"""
    files_by_date = {}
    special_files = []

    # S3 버킷에서 모든 객체 가져오기
    response = s3_client.list_objects_v2(Bucket=AWS_S3_BUCKET_NAME)

    if 'Contents' in response:
        # print(response['Contents'])
        for obj in response['Contents']:
            key = obj['Key']
            size = obj['Size']
            print(obj)
            if key.startswith('special/'):
                try:
                    if size == 0:
                        pass
                    else:
                        _, date_folder = key.split('/', 2)
                        special_files.append(key.replace('special/', ''))
                except ValueError:
                    pass

            elif key.startswith('uploads/'):
                try:
                    if size == 0:
                        pass
                    else:
                        _, date_folder, filename = key.split('/', 2)
                        if date_folder not in files_by_date:
                            files_by_date[date_folder] = []
                            files_by_date[date_folder].append(filename)
                except ValueError:
                    pass

    return render_template('index.html', files_by_date=files_by_date, special_files=special_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """파일을 S3에 업로드"""
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if 'special_type' in request.form:
        # 특별 파일 업로드 (success_update.zip 또는 fail_update.zip)
        special_type = request.form['special_type']
        if special_type == 'success_update':
            filename = 'success_update.zip'
        elif special_type == 'fail_update':
            filename = 'fail_update.zip'
        else:
            return redirect(request.url)

        s3_key = f"special/{filename}"
        s3_client.upload_fileobj(file, AWS_S3_BUCKET_NAME, s3_key)
        return redirect(url_for('index'))

    # 일반 파일 업로드 처리
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        current_time = datetime.now().strftime('%H%M%S')
        filename = f"{original_filename.rsplit('.', 1)[0]}_{current_time}.{original_filename.rsplit('.', 1)[1]}"
        
        # 날짜별 폴더 지정
        date_folder = datetime.now().strftime('%Y-%m-%d')
        s3_key = f"uploads/{date_folder}/{filename}"

        # S3에 파일 업로드
        s3_client.upload_fileobj(file, AWS_S3_BUCKET_NAME, s3_key)

        return redirect(url_for('index'))

    return redirect(request.url)

@app.route('/download/special/<filename>')
def download_special_file(filename):
    """특별 파일 다운로드 링크 생성"""
    s3_key = f"special/{filename}"
    
    try:
        url = s3_client.generate_presigned_url('get_object', 
                                               Params={'Bucket': AWS_S3_BUCKET_NAME, 'Key': s3_key}, 
                                               ExpiresIn=3600)  # 1시간 유효한 다운로드 URL 생성
        return redirect(url)
    except Exception:
        abort(404)

@app.route('/download/<date_folder>/<filename>')
def download_file(date_folder, filename):
    """일반 파일 다운로드 링크 생성"""
    s3_key = f"uploads/{date_folder}/{filename}"
    
    try:
        url = s3_client.generate_presigned_url('get_object', 
                                               Params={'Bucket': AWS_S3_BUCKET_NAME, 'Key': s3_key}, 
                                               ExpiresIn=3600)  # 1시간 유효한 다운로드 URL 생성
        return redirect(url)
    except Exception:
        abort(404)

@app.route('/delete/<date_folder>/<filename>', methods=['POST'])
def delete_file(date_folder, filename):
    """일반 파일 S3에서 삭제"""
    s3_key = f"uploads/{date_folder}/{filename}"
    
    try:
        s3_client.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=s3_key)
    except Exception:
        pass
    
    return redirect(url_for('index'))

@app.route('/delete/special/<filename>', methods=['POST'])
def delete_special_file(filename):
    """특별 파일 S3에서 삭제"""
    s3_key = f"special/{filename}"
    
    try:
        s3_client.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=s3_key)
    except Exception:
        pass

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True,port=8080)
