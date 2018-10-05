
from sbxpy.QueryBuilder import QueryBuilder as Qb
import aiohttp
import asyncio
from threading import Thread

'''
:mod:`sbxpy` -- Main Library
===================================
.. module:: sbxpy
   :platform: Unix, Windows
   :synopsis:  This is the module that use QueryBuilder to create all request used to communicate with SbxCloud
.. moduleauthor:: Luis Guzman <lgguzman890414@gmail.com>  
'''


class Find:

    def __init__(self, model, sbx_core):
        self.query = Qb().set_domain(SbxCore.environment['domain']).set_model(model)
        self.lastANDOR = None
        self.sbx_core = sbx_core
        self.url = SbxCore.urls['find']

    def compile(self):
        return self.query.compile()

    def new_group_with_and(self):
        self.query.new_group('AND')
        self.lastANDOR = None
        return self

    def new_group_with_or(self):
        self.query.new_group('OR')
        self.lastANDOR = None
        return self

    def and_where_is_equal(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '=', value)
        return self

    def and_where_is_not_null(self, field):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'IS NOT', None)
        return self

    def and_where_is_null(self, field):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'IS', None)
        return self

    def and_where_greater_than(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '>', value)
        return self

    def and_where_less_than(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '<', value)
        return self

    def and_where_greater_or_equal_than(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '>=', value)
        return self

    def and_where_less_or_equal_than(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '<=', value)
        return self

    def and_where_is_not_equal(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, '!=', value)
        return self

    def and_where_starts_with(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', '%' + value)
        return self

    def and_where_ends_with(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', value + '%')
        return self

    def and_where_contains(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', '%' + value + '%')
        return self

    def and_where_in(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'IN', value)
        return self

    def and_where_not_in(self, field, value):
        self.lastANDOR = 'AND'
        self.query.add_condition(self.lastANDOR, field, 'NOT IN', value)
        return self

    def or_where_is_equal(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '=', value)
        return self

    def or_where_is_not_null(self, field):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'IS NOT', None)
        return self

    def or_where_is_null(self, field):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'IS', None)
        return self

    def or_where_greater_than(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '>', value)
        return self

    def or_where_less_than(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '<', value)
        return self

    def or_where_greater_or_equal_than(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '>=', value)
        return self

    def or_where_less_or_equal_than(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '<=', value)
        return self

    def or_where_is_not_equal(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, '!=', value)
        return self

    def or_where_starts_with(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', '%' + value)
        return self

    def or_where_ends_with(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', value + '%')
        return self

    def or_where_contains(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'LIKE', '%' + value + '%')
        return self

    def or_where_in(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'IN', value)
        return self

    def or_where_not_in(self, field, value):
        self.lastANDOR = 'AND' if (self.lastANDOR is None) else 'OR'
        self.query.add_condition(self.lastANDOR, field, 'NOT IN', value)
        return self

    def or_where_reference_join_between(self, field, reference_field):
        return ReferenceJoin(self, field, reference_field, 'OR')

    def and_where_reference_join_between(self, field, reference_field):
        return ReferenceJoin(self, field, reference_field, 'AND')

    def where_with_keys(self, keys):
        self.query.where_with_keys(keys)
        return self

    def order_by(self, field, asc):
        self.query.order_by(field, asc)
        return self

    def fetch_models(self, array):
        self.query.fetch_models(array)
        return self

    def set_page(self, page):
        self.query.set_page(page)
        return self

    def set_page_size(self, size):
        self.query.set_page_size(size)
        return self

    async def __then(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.sbx_core.p(self.url), json=self.compile(),
                    headers=self.sbx_core.get_headers_json()) as resp:
                return await resp.json()

    def set_url(self, is_find):
        self.url = SbxCore.urls['find'] if is_find else SbxCore.urls['delete']

    async def find(self):
        self.set_url(True)
        return await self.__then()

    def findCallback(self, callback):
        self.sbx_core.make_callback(self.find(), callback)


class ReferenceJoin:

    def __init__(self, find, field, reference_field, types):
        self.find = find
        self.field = field
        self.reference_field = reference_field
        if types == 'AND':
            self.find.and_where_in(self.field, '@reference_join@')
        else:
            self.find.or_where_in(self.field, '@reference_join@')

    def in_model(self, reference_model):
        return FilterJoin(self.find, self.field, self.reference_field, reference_model)


class FilterJoin:

    def __init__(self, find, field, reference_field, reference_model):
        self.find = find
        self.field = field
        self.reference_field = reference_field
        self.reference_model = reference_model

    def filter_where_is_equal(self, value):
        self.find.query.setReferenceJoin('=', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_is_not_null(self, value):
        self.find.query.setReferenceJoin('IS NOT', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_is_null(self, value):
        self.find.query.setReferenceJoin('IS', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_greater_than(self, value):
        self.find.query.setReferenceJoin('>', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_less_than(self, value):
        self.find.query.setReferenceJoin('<', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_greater_or_equal_than(self, value):
        self.find.query.setReferenceJoin('>=', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_less_or_equal_than(self, value):
        self.find.query.setReferenceJoin('<=', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_is_not_equal(self, value):
        self.find.query.setReferenceJoin('!=', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_like(self, value):
        self.find.query.setReferenceJoin('LIKE', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_in(self, value):
        self.find.query.setReferenceJoin('IN', self.field, self.reference_field, self.reference_model, value)
        return self.find

    def filter_where_not_in(self, value):
        self.find.query.setReferenceJoin('NOT IN', self.field, self.reference_field, self.reference_model, value)
        return self.find


class SbxCore:
    '''
        This is the core of the communication with SbxCloud.
        The concurrent task operates with asyncio
        The request operates with aiohttp
    '''
    environment = {}
    headers = {}
    urls = {
        'update_password': '/user/v1/password',
        'login': '/user/v1/login',
        'register': '/user/v1/register',
        'validate': '/user/v1/validate',
        'row': '/data/v1/row',
        'find': '/data/v1/row/find',
        'update': '/data/v1/row/update',
        'delete': '/data/v1/row/delete',
        'downloadFile': '/content/v1/download',
        'uploadFile': '/content/v1/upload',
        'addFolder': '/content/v1/folder',
        'folderList': '/content/v1/folder',
        'send_mail': '/email/v1/send',
        'payment_customer': '/payment/v1/customer',
        'payment_card': '/payment/v1/card',
        'payment_token': '/payment/v1/token',
        'password': '/user/v1/password/request',
        'cloudscript_run': '/cloudscript/v1/run'
    }

    def __init__(self, manage_loop=False):
        '''
        Create a instance of SbxCore.
        :param manage_loop: if the event loop is manage by the library
        '''
        self.loop = None
        self.t = None
        if manage_loop:
            def start_loop():
                print('loop started')
                self.loop.run_forever()

            self.loop = asyncio.new_event_loop()
            self.t = Thread(target=start_loop)
            self.t.start()



    def get_headers_json(self):
        SbxCore.headers['Content-Type'] = 'application/json'
        return SbxCore.headers

    def p(self, path):
        return SbxCore.environment['base_url'] + path

    def initialize(self, domain, app_key, base_url):
        SbxCore.environment['domain'] = domain
        SbxCore.environment['base_url'] = base_url
        SbxCore.environment['app_key'] = app_key
        SbxCore.headers['App-Key'] = app_key
        return self

    def with_model(self, model):
        return Find(model, self)

    def upsert(self, model, data, let_null):
        return self.query_builder_to_insert(data, let_null).setModel(model).compile()

    def query_builder_to_insert(self, data, let_null):
        query = Qb().set_domain(SbxCore.environment['domain'])
        if isinstance(data, list):
            for item in data:
                query.add_object(self.validate_data(item, let_null))
        else:
            query.add_object(self.validate_data(data, let_null))
        return query

    def validate_data(self, data, let_null):
        listkeys = [key for key in data if let_null or data[key] is not None]
        temp = {}
        for key in listkeys:
            if data[key] is not None and isinstance(data[key], dict) and '_KEY' in data[key]:
                data[key] = data[key]['_KEY']
            temp[key] = data[key]
        return temp

    '''
    ======================================
    Async Functions
    ======================================
    '''

    async def login(self, login, password, domain):
        async with aiohttp.ClientSession() as session:
            params = {'login': login, 'password': password, 'domain': domain}
            async with session.get(self.p(self.urls['login']), params=params, headers=self.get_headers_json()) as resp:
                data = await resp.json()
                if data['success']:
                    self.headers['Authorization'] = 'Bearer ' + data['token']
                return data


    async def run(self, key, params):
        async with aiohttp.ClientSession() as session:
            params = {'key': key, 'params': params}
            async with session.post(self.p(self.urls['cloudscript_run']),params=params, headers=self.get_headers_json()) as resp:
                return await resp.json()


    '''
    ======================================
    Callback Functions
    ======================================
    '''

    def loginCallback(self, login, password, domain, call):
        self.make_callback(self.login(login, password, domain),call)

    def make_callback(self, courutine, call):
        try:
            if self.loop is None:
                raise Exception('SbxCore must initialize with manage_loop True')
            else:
                # future = asyncio.ensure_future(
                #    courutine, loop=self.loop)
                def callback(fut):
                    call(None, fut.result())
                # future.add_done_callback(callback)

                future= asyncio.run_coroutine_threadsafe(courutine, loop = self.loop)
                future.add_done_callback(callback)
        except Exception as inst:
            call(inst, None)





    def close_connection(self):
        if self.loop is not None:
            if self.loop.is_running():
                asyncio.gather(*asyncio.Task.all_tasks()).cancel()
                self.loop.stop()