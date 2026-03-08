import requests
import re
import time
import random
import json
import os

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Host": "www.luogu.com.cn"
}

def upd_c3vk(session, response):
    match = re.search(r'C3VK=([a-f0-9]+)', response.text)
    if match:
        session.cookies.set('C3VK', match.group(1), domain='.luogu.com.cn', path='/')

def login(session):
    response = session.get("https://www.luogu.com.cn/auth/login")
    upd_c3vk(session, response)

    _t = time.time() * 1000 + random.random()
    response = session.get(f"https://www.luogu.com.cn/lg4/captcha?_t={_t}")
    if response.status_code != 200:
        print(f"验证码获取失败: {response.status_code}")
        return None

    with open("captcha.png", "wb") as f:
        f.write(response.content)
    print("验证码已保存为 captcha.png")
    captcha = input("请输入验证码: ")

    if not os.path.exists("config.json"):
        with open("config.json", "w") as f:
            json.dump({}, f, indent=4)

    with open("config.json", "r") as f:
        config = json.load(f)
        if "username" in config:
            username = config["username"]
        else:
            username = input("请输入用户名: ")
            remember_me = input("是否记住用户名? (Y/n): ") or "Y"
            if remember_me.lower() == "y":
                config["username"] = username
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=4)
        if "password" in config:
            password = config["password"]
        else:
            password = input("请输入密码: ")
            remember_me = input("是否记住密码? (Y/n): ") or "Y"
            if remember_me.lower() == "y":
                config["password"] = password
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=4)
    login_headers = headers.copy()
    login_headers.update({
        "Referer": "https://www.luogu.com.cn/auth/login",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json"
    })
    response = session.post(
        "https://www.luogu.com.cn/do-auth/password",
        headers = login_headers,
        json = {
            "username": username,
            "password": password,
            "captcha": captcha
        }
    )
    if response.status_code == 200:
        print("登录成功")
    else:
        print(f"登录失败: {json.loads(response.text)['errorMessage']}")
    upd_c3vk(session, response)
    
if __name__ == "__main__":
    session = requests.Session()
    session.headers.update(headers)
    login(session)
    # 测试：添加云剪贴板
    response = session.get(
        "https://www.luogu.com.cn/paste",
        headers = {
            "Referer": "https://www.luogu.com.cn/auth/login",
        }
    )
    print(response.status_code)
    upd_c3vk(session, response)

    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)">', response.text)
    if not csrf_match:
        print("无法获取CSRF Token，请求将失败")
        exit(1)
    csrf_token = csrf_match.group(1)
    print(f"获取到CSRF Token: {csrf_token}")

    post_headers = headers.copy()
    post_headers.update({
        "Referer": "https://www.luogu.com.cn/paste",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.luogu.com.cn",
        "Priority": "u=1, i",
        "Sec-Ch-Ua": '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Csrf-Token": csrf_token
    })
    response = session.post(
        "https://www.luogu.com.cn/paste/new",
        headers = post_headers,
        json = {
            "public": True,
            "data": f"Hello world! ({time.time()})"
        }
    )
    print(response.status_code)
    print(response.text)

