from sanic import Sanic, app,response
from jinja2 import Environment,FileSystemLoader,select_autoescape
import sys
import json
import io_middleware

app = Sanic(__name__)
enable_async = sys.version_info >= (3, 6)
jinja2_env = Environment(
    loader = FileSystemLoader('templates'),
    autoescape=select_autoescape(['html','xml']),
    enable_async=enable_async
)
io_m = None

async def render_template(template_name,**kwargs):
    raw_template = jinja2_env.get_template(template_name)
    print(kwargs)
    rendered_template = await raw_template.render_async(kwargs=kwargs)
    return rendered_template

@app.listener("before_server_start")
async def initialize(app,loop):
    global io_m 
    io_m = io_middleware.IOMiddleware()
    await io_m.init()

@app.route('/')
async def index(request):
    return response.html(await render_template('index.html',notice = 'HelloWorld powered by Sanic'))

@app.route('/signin',methods=['GET','POST'])
async def signin(request):
    if request.method == 'GET':
        return response.html(await render_template('signin.html'))
    elif request.method == 'POST':
        account = request.form.get('account',None)
        password = request.form.get('password',None)
        hidden   = request.form.get('hidden',None)
        if not account or not password:
            return response.text("账号或密码为空")
        else:
            valid,token = await io_m.sign_in(account,password)
            if valid == True:
                return response.html(f"""登录成功！你的token是：{token}""")
            else:
                return response.html(f"""登陆失败！账号或密码错误""")

@app.route('/signup',methods=['GET','POST'])
async def signup(request):
    if request.method == 'GET':
        return response.html(await render_template('signup.html'))
    elif request.method == 'POST':
        account = request.form.get('account',None)
        password = request.form.get('password',None)
        repeat_pass = request.form.get('repeat',None)
        hidden = request.form.get('hidden',None)
        if not account or not password:
            return response.text("账号或密码为空")
        else:
            if password == repeat_pass:
                result,reason = await io_m.sign_up(account,password)
                if result == True:
                    return response.html(f"""注册成功""")
                else:
                    if reason == 0:
                        return response.html(f"""账号已经被使用""")
            else:
                return response.text("两次输入密码不一致")

@app.route('/api/v0/signin',methods=['POST'])
async def api_signin(request):
    account = request.form.get('account',None)
    password = request.form.get('password',None)
    hidden   = request.form.get('hidden',None)
    if not account or not password:
        return response.json({'result':'fail','detail':'Empty account or password'})
    else:
        valid,token = await io_m.sign_in(account,password)
        if valid == True:
            return response.json({'result':'success','token':token})
        else:
            return response.json({'result':'fail','detail':'Wrong account or passwords'})

@app.route('/api/v0/minecraft/checkbind/<account>',methods=['GET'])
async def api_minecraft_checkbind(request,account):
    result = await io_m.minecraft_checkbind(account)
    if result == 1:
        return response.json({'result':'success','detail':'Verified'})
    elif result == 0:
        return response.json({'result':'success','detail':'Not verified'})
    elif result == 2:
        return response.json({'result':'success','detail':'Not registered'})

@app.route('/api/v0/minecraft/bind',methods=['GET','POST'])
async def api_minecraft_bind(request):
    if request.method == 'GET':
        account = request.args.get('account',None)
        minecraft_account = request.args.get('minecraft_account',None)
        if not all([account,minecraft_account]):
            return response.json({'result':'fail','detail':'Missing arguments.'})
        else:
            result,code =  await io_m.minecraft_bind_get(account,minecraft_account)
            if result == False:
                return response.json({'result':'fail','detail':'Already binded'})
            elif result == True:
                return response.json({'result':'success','detail':'Here is your code.','code':code})
    if request.method == 'POST':
        account = request.form.get('account',None)
        minecraft_account = request.form.get('minecraft_account',None)
        code = request.form.get('code',None)
        if not all([account,minecraft_account,code]):
            return response.json({'result':'fail','detail':'Missing arguments.'})
        else:
            result = await io_m.minecraft_bind_post(account,minecraft_account,code)
            if result == 1:
                return response.json({'result':'success','detail':f'Successfully bind {minecraft_account} to {account}!'})
            if result == 0:
                return response.json({'result':'fail','detail':'Code not exist or is expired.'})
            if result == 2:
                return response.json({'result':'fail','detail':'Cannot pull your information from Mojang\'s server.'})

@app.route('/minecraft/bind',methods=['GET'])
async def minecraft_bind(request):
    return response.html(await render_template('minecraft_bind.html',notice = 'HelloWorld powered by Sanic'))

if __name__ == '__main__':
    app.run(host='localhost',port=8090,debug=True)
