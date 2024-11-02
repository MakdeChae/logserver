import os
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 기본 업로드 폴더 및 특정 파일 저장 경로 설정
UPLOAD_FOLDER = 'uploads'
SPECIAL_FOLDER = 'special_files'
ALLOWED_EXTENSIONS = {'zip'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SPECIAL_FOLDER'] = SPECIAL_FOLDER

# 기본 업로드 폴더와 특정 파일 저장 폴더가 없으면 생성
for folder in [UPLOAD_FOLDER, SPECIAL_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 파일 확장자를 확인하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # 날짜별 파일과 특정 파일 목록을 함께 렌더링
    date_folders = sorted(os.listdir(app.config['UPLOAD_FOLDER']), reverse=True)
    files_by_date = {
        date_folder: os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], date_folder))
        for date_folder in date_folders
    }
    special_files = os.listdir(app.config['SPECIAL_FOLDER'])
    return render_template('index.html', files_by_date=files_by_date, special_files=special_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    # 요청에 파일이 포함되어 있는지 확인
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    # 파일이 선택되지 않은 경우 리다이렉트
    if file.filename == '':
        return redirect(request.url)

    # Success Update 또는 Fail Update 파일 업로드 처리
    if 'special_type' in request.form:
        special_type = request.form['special_type']
        if special_type == 'success_update':
            filename = 'success_update.zip'
        elif special_type == 'fail_update':
            filename = 'fail_update.zip'
        else:
            return redirect(request.url)

        # 파일을 특별 파일 폴더에 저장
        file.save(os.path.join(app.config['SPECIAL_FOLDER'], filename))
        return redirect(url_for('index'))

    # 일반 파일 업로드 처리 (날짜별 폴더에 저장)
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        current_time = datetime.now().strftime('%H%M%S')
        filename = f"{original_filename.rsplit('.', 1)[0]}_{current_time}.{original_filename.rsplit('.', 1)[1]}"
        
        # 현재 날짜로 된 폴더 생성
        date_folder = datetime.now().strftime('%Y-%m-%d')
        date_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], date_folder)
        
        if not os.path.exists(date_folder_path):
            os.makedirs(date_folder_path)
        
        file.save(os.path.join(date_folder_path, filename))
        return redirect(url_for('index'))

    return redirect(request.url)

# 특정 파일 다운로드 라우트
@app.route('/download/special/<filename>')
def download_special_file(filename):
    file_path = os.path.join(app.config['SPECIAL_FOLDER'], filename)
    if not os.path.exists(file_path):
        abort(404)  # 파일이 존재하지 않으면 404 오류 발생
    return send_from_directory(app.config['SPECIAL_FOLDER'], filename)

# 날짜별 파일 다운로드 라우트
@app.route('/download/<date_folder>/<filename>')
def download_file(date_folder, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], date_folder), filename)

# 날짜별 파일 삭제 라우트
@app.route('/delete/<date_folder>/<filename>', methods=['POST'])
def delete_file(date_folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], date_folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
