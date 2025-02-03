from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import logging

app = Flask(__name__)
CORS(app)

# 添加日志配置
logging.basicConfig(level=logging.DEBUG)

# 确保数据库和头像目录存在
if not os.path.exists('database'):
    os.makedirs('database')
if not os.path.exists('static/avatars'):
    os.makedirs('static/avatars')

# 添加 CORS 支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# 处理预检请求
@app.route('/register', methods=['OPTIONS'])
def handle_options():
    return '', 204

# 初始化数据库
def init_db():
    try:
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        # 创建用户表
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                password TEXT NOT NULL,
                avatar TEXT DEFAULT 'default.png'
            )
        ''')
        
        # 创建反馈表
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                content TEXT NOT NULL,
                submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        app.logger.info("数据库初始化成功")
    except Exception as e:
        app.logger.error(f"数据库初始化失败: {str(e)}")

# 确保在应用启动时初始化数据库
init_db()

# 处理根路径请求
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# 处理其他静态文件
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# 处理 favicon 请求
@app.route('/favicon.ico')
def favicon():
    return '', 204

# 注册新用户
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            app.logger.error("没有接收到JSON数据")
            return jsonify({
                'success': False,
                'message': '注册失败：数据格式错误'
            })

        nickname = data.get('nickname')
        password = data.get('password')
        
        if not nickname or not password:
            app.logger.error("昵称或密码为空")
            return jsonify({
                'success': False,
                'message': '注册失败：昵称和密码不能为空'
            })

        app.logger.info(f"尝试注册用户: {nickname}")
        
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        
        c.execute('INSERT INTO users (nickname, password) VALUES (?, ?)', 
                 (nickname, password))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        
        app.logger.info(f"用户注册成功，ID: {user_id}")
        return jsonify({
            'success': True,
            'message': f'注册成功！你的ID是：{user_id}',
            'id': user_id
        })
    except Exception as e:
        app.logger.error(f"注册过程中出现错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'注册失败：{str(e)}'
        })

# 用户登录
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user_id = data.get('id')
        password = data.get('password')
        
        app.logger.info(f"尝试登录，ID: {user_id}")
        
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        
        c.execute('SELECT nickname, password FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if user is None:
            app.logger.info(f"ID {user_id} 不存在")
            return jsonify({
                'success': False,
                'message': '此id不存在，请检查id或注册一个新账号'
            })
        
        if user[1] != password:
            app.logger.info(f"ID {user_id} 密码不匹配")
            return jsonify({
                'success': False,
                'message': '密码和id不匹配，请重新尝试'
            })
        
        app.logger.info(f"用户 {user[0]} 登录成功")
        return jsonify({
            'success': True,
            'message': f'登录成功！欢迎你！{user[0]}',
            'nickname': user[0]
        })
    except Exception as e:
        app.logger.error(f"登录过程中出现错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'登录失败：{str(e)}'
        })

# 添加清空数据库的路由
@app.route('/clear_database', methods=['GET'])
def clear_database():
    try:
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        return jsonify({
            'success': True,
            'message': '数据库已清空'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清空数据库失败：{str(e)}'
        })

# 添加更新用户信息的路由
@app.route('/update_user', methods=['POST'])
def update_user():
    try:
        data = request.get_json()
        user_id = data.get('id')
        nickname = data.get('nickname')
        password = data.get('password')
        
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        
        if nickname:
            c.execute('UPDATE users SET nickname = ? WHERE id = ?', (nickname, user_id))
        if password:
            c.execute('UPDATE users SET password = ? WHERE id = ?', (password, user_id))
            
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '更新成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        })

# 添加上传头像的路由
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    try:
        user_id = request.form.get('id')
        file = request.files['avatar']
        
        if file:
            # 生成文件名
            filename = f'avatar_{user_id}.png'
            # 保存文件
            file.save(os.path.join('static/avatars', filename))
            
            # 更新数据库
            conn = sqlite3.connect('database/users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET avatar = ? WHERE id = ?', (filename, user_id))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': '头像上传成功'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'上传失败：{str(e)}'
        })

# 添加获取头像的路由
@app.route('/get_avatar')
def get_avatar():
    try:
        user_id = request.args.get('id')
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        c.execute('SELECT avatar FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'avatar': result[0]
            })
        return jsonify({
            'success': False,
            'message': '用户不存在'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# 添加获取密码的路由
@app.route('/get_password')
def get_password():
    try:
        user_id = request.args.get('id')
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'password': result[0]
            })
        return jsonify({
            'success': False,
            'message': '用户不存在'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# 修改反馈处理路由，添加 OPTIONS 方法支持
@app.route('/submit_feedback', methods=['POST', 'OPTIONS'])
def submit_feedback():
    # 处理 OPTIONS 请求
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        user_id = data.get('userId')
        content = data.get('content')
        
        if not user_id or not content:
            return jsonify({
                'success': False,
                'message': '提交失败：用户ID和反馈内容不能为空'
            })
        
        # 获取用户昵称
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        
        # 先获取用户昵称
        c.execute('SELECT nickname FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({
                'success': False,
                'message': '提交失败：用户不存在'
            })
            
        nickname = user[0]
        
        # 保存反馈信息
        c.execute('''
            INSERT INTO feedback (user_id, nickname, content)
            VALUES (?, ?, ?)
        ''', (user_id, nickname, content))
        
        conn.commit()
        conn.close()
        
        app.logger.info(f"用户 {nickname}(ID: {user_id}) 提交了反馈")
        return jsonify({
            'success': True,
            'message': '反馈提交成功'
        })
    except Exception as e:
        app.logger.error(f"提交反馈时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'提交失败：{str(e)}'
        })

# 添加获取反馈列表的路由
@app.route('/get_feedback')
def get_feedback():
    try:
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        c.execute('''
            SELECT id, user_id, nickname, content, submit_time
            FROM feedback
            ORDER BY submit_time DESC
        ''')
        feedback_list = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'feedback': [{
                'id': f[0],
                'userId': f[1],
                'nickname': f[2],
                'content': f[3],
                'submitTime': f[4]
            } for f in feedback_list]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# 添加获取用户列表的路由
@app.route('/get_users')
def get_users():
    try:
        conn = sqlite3.connect('database/users.db')
        c = conn.cursor()
        c.execute('SELECT id, nickname, password FROM users ORDER BY id')
        users = c.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'users': [{
                'id': u[0],
                'nickname': u[1],
                'password': u[2]
            } for u in users]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    print("正在启动服务器...")
    print("请在浏览器中访问: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)
