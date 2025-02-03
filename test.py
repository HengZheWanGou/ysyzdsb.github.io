from flask import Flask
import sys

print(f"Python 版本: {sys.version}")
print("正在创建 Flask 应用...")

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    print("服务器正在启动...")
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"启动失败: {str(e)}")