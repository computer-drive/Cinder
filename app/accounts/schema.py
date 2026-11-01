MS_CLIENT_ID = "ba0066a5-1eee-4e44-bf56-5687702e170c" # Microsoft 客户端 ID
MS_BASE_URL = "https://login.microsoftonline.com/"

REDIRECT_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cinder</title>
    <style>
        .container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
        }

        h1, h2 {
            font-weight: normal;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>登录成功</h1>
        <h2>你已经成功登录到了 Microsoft 账户，现在你可以关闭浏览器窗口了。</h2>
    </div>
</body>
</html>'''

REDIRECT_PAGE_ERROR = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cinder</title>
    <style>
        .container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
        }

        h1, h2 {
            font-weight: normal;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>错误</h1>
        <h2>未获取到 Microsoft 账户的访问令牌。</h2>
    </div>
</body>
</html>'''

XBOX_LIVE_URL = "https://user.auth.xboxlive.com/user/authenticate"


def get_xobx_live_body(refresh_token: str):
    return  {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={refresh_token}"   
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }

XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"

MC_TOKEN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"