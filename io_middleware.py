import os
import json
import hashlib
import datetime
from re import T
import aiohttp

class IOMiddleware:
    def __init__(self):
        self.usemysql = __import__('usemysql')

    async def init(self):
        self.um = self.usemysql.UseMysql()
        pool = await self.um.initpool()
        self.um.pool = pool

    async def sign_up(self,account,password):
        result = await self.api_check_account_availability(account)
        if result:
            pass_salt = self.newsalt(16)
            pass_hash = self.gethash(password,pass_salt)
            await self.um.sign_up(account,pass_hash,pass_salt)
            return True,1
        else:
            return False,0

    async def api_check_account_availability(self,account):
        result = await self.um.check_account_availability(account)
        return result

    async def sign_in(self,account,pass_input):
        pass_hash,pass_salt = await self.um.query_auth(account)
        if not pass_hash or not pass_salt:
            return False,False
        else:
            hash_output = self.gethash(pass_input,pass_salt)
            if hash_output == pass_hash:
                my_token = await self.gettoken(account)
                return True,my_token
            else:
                return False,False

    async def gettoken(self,account):
        my_token = self.newsalt(32)
        await self.um.storetoken(account,my_token)
        return my_token
    async def checktoken(self,account):
        pass
    async def refreshtoken(self,account):
        pass

    def gethash(self,pass_input,pass_salt):
        input_combine = pass_input + pass_salt
        hash_input = hashlib.md5()
        hash_input.update(input_combine.encode("utf8"))
        hash_output = hash_input.hexdigest()
        return hash_output

    def newsalt(self,length):
        return ''.join(
                    map(
                        # lambda x:('/x' if len(hex(x))>=4 else '/x0') + hex(x)[2:] , os.urandom(16)
                        lambda x: ('' if len(hex(x))>=4 else '0') + hex(x)[2:],
                        os.urandom(length)
                    )
                )
        #以上面的注释语句为例，从内到外分析
        #os.urandom() 
        #   This function returns random bytes from an OS-specific randomness source.
        #   The returned data should be unpredictable enough for cryptographic applications, 
        #   though its exact quality depends on the OS implementation.
        #   On Windows, it will use CryptGenRandom() to work.
        #Reference: https://docs.python.org/3/library/os.html
        #os.urandom(16) 会生成一个16字节的 bytes 对象，用 list() 可以将每一位作为列表的一项，并返回一个列表
        #实际使用中不加 list() 也可以
        #lambda 匿名函数：对于给定的 x ，做冒号之后的操作并返回结果，如 lambda x: x + 1 将会得到2
        #在这里，对于给定x，将其转换为 16 进制（形如'0x1b'）的字符串后，进行判断
        #如果字符串长度 >= 4 就返回字符串'/x'，即不用补足0；如果不足4位，则补一个0
        #在实际使用中由于不需要'/x'标志指示 16 进制，所以仅返回''或者'0'
        #之后，再将返回结果加上实际 16 进制后的值，得到新的一项
        #map(操作函数, 一个或多个序列, ...)，将序列中的每一项取出，运行给定的操作函数得到返回值，用其替换序列中的原值
        #在这里 lambda 匿名函数是操作函数，os.urandom(16) 是一个序列，经过操作，原序列变成每一项都只有两个字符的新序列
        #str.join(序列)，其中str是连接符号，这里不需要所以为空；序列是map函数返回的新序列

    def gettime(self,method='now',days=0,hours=0,minutes=0,seconds=0):
        if method == 'now':
            return ((datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S"))
        elif method == 'forward':
            return  ((datetime.datetime.now()
                    +datetime.timedelta(days=days,hours=hours,minutes=minutes,seconds=seconds))
                    .strftime("%Y-%m-%d %H:%M:%S"))
        elif method == 'backward':
            return  ((datetime.datetime.now()
                    -datetime.timedelta(days=days,hours=hours,minutes=minutes,seconds=seconds))
                    .strftime("%Y-%m-%d %H:%M:%S"))

    async def minecraft_checkbind(self,account):
        result = await self.um.minecraft_checkbind(account)
        return result

    async def minecraft_bind_get(self,account,minecraft_account):
        result = await self.minecraft_checkbind(account)
        if result == 1:
            return False,None
        if result == 2:
            await self.um.minecraft_init_account(account)
        new_code = self.newsalt(3)
        expire_time = self.gettime(method='forward',hours=1)
        await self.um.minecraft_store_bind_code(account,minecraft_account,new_code,expire_time)
        return True,new_code

    async def minecraft_bind_post(self,account,minecraft_account,code):
        result,true_code,expire_time = await self.um.minecraft_getcode(account,code)
        if result == True:
            now_time = datetime.datetime.strptime(self.gettime(method='now'), "%Y-%m-%d %H:%M:%S")
            if now_time >= expire_time:
                return 0
            else:
                if code == true_code:
                    result,uuid = await self.minecraft_pull_information(minecraft_account)
                    if result == True:
                        await self.um.minecraft_store_uuid(account,uuid,now_time)
                        return 1
                    elif result == False:
                        return 2
        elif result == False:
            return 0

    async def minecraft_pull_information(self,minecraft_account):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.mojang.com/users/profiles/minecraft/{minecraft_account}') as resp:
                result = await resp.json()
                print(f"""=====>成功向Mojang取得json请求体\n=====>{result}""")
        return True,result['id']

# async def testfunc():
#     test = IOMiddleware()
#     await test.init()
#     #print(await test.sign_up("asakirain","ssr129631"))
#     # print(await test.sign_in("asakirain","ssr129631"))
#     #print(await test.gettoken(account='asakirain'))
    
# loop = asyncio.get_event_loop()
# loop.run_until_complete(testfunc())