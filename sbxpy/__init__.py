from sbxpy.QueryBuilder import QueryBuilder as Qb
import aiohttp
import asyncio
import copy
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
        self.query = Qb().set_domain(sbx_core.environment['domain']).set_model(model)
        self.lastANDOR = None
        self.sbx_core = sbx_core
        self.url = self.sbx_core.urls['find']

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

    async def __then(self, query_compiled):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.sbx_core.p(self.url), json=query_compiled,
                    headers=self.sbx_core.get_headers_json()) as resp:
                return await resp.json()

    def set_url(self, is_find):
        self.url = self.sbx_core.urls['find'] if is_find else self.sbx_core.urls['delete']

    async def find(self):
        self.set_url(True)
        return await self.__then(self.query.compile())

    def find_callback(self, callback):
        self.sbx_core.make_callback(self.find(), callback)

    async def find_all_query(self):
        self.set_page_size(500)
        self.set_url(True)
        queries = []
        query_compiled = self.query.compile()
        data = await self.__then(query_compiled)
        total_pages = data['total_pages']
        for i in range(total_pages):
            query_aux = copy.deepcopy(query_compiled)
            query_aux['page'] = (i + 1)
            queries.append(self.__then(query_aux))
        futures = self.__chunk_it(queries, min(10, len(queries)))
        results = await asyncio.gather(*[futures[i] for i in range(len(futures))])
        data = []
        for i in range(len(results)):
            for j in range(len(results[i])):
                data.append(results[i][j])
        return data

    def find_all_callback(self, callback):
        self.sbx_core.make_callback(self.find_all_query(), callback)

    def __chunk_it(self, seq, num):
        avg = len(seq) / float(num)
        out = []
        last = 0.0

        while last < len(seq):
            out.append(asyncio.gather(*seq[int(last):int(last + avg)]))
            last += avg

        return out


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
        'delete': '/data/v1/row/',
        'downloadFile': '/content/v1/download',
        'uploadFile': '/content/v1/upload',
        'addFolder': '/content/v1/folder',
        'folderList': '/content/v1/folder',
        'send_mail': '/email/v1/send',
        'payment_customer': '/payment/v1/customer',
        'payment_card': '/payment/v1/card',
        'payment_token': '/payment/v1/token',
        'password': '/user/v1/password/request',
        'cloudscript_run': '/cloudscript/v1/run',
        'domain': '/data/v1/row/model/list'
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
        self.headers['Content-Type'] = 'application/json'
        return self.headers

    def p(self, path):
        return self.environment['base_url'] + path

    def initialize(self, domain, app_key, base_url):
        self.environment['domain'] = domain
        self.environment['base_url'] = base_url
        self.environment['app_key'] = app_key
        self.headers['App-Key'] = app_key
        return self

    def with_model(self, model):
        return Find(model, self)

    def query_builder_to_insert(self, data, let_null):
        query = Qb().set_domain(self.environment['domain'])
        if isinstance(data, list):
            for item in data:
                query.add_object(self.validate_data(item, let_null))
        else:
            query.add_object(self.validate_data(data, let_null))
        return query

    def is_update(self, data):
        sw = False
        if isinstance(data, list):
            for item in data:
                if "_KEY" in item:
                    sw = True
        else:
            if "_KEY" in data:
                sw = True
        return sw

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

    async def list_domain(self):
        async with aiohttp.ClientSession() as session:
            params = {'domain':  self.environment['domain']}
            async with session.get(self.p(self.urls['domain']), params=params, headers=self.get_headers_json()) as resp:
                return await resp.json()

    async def run(self, key, params):
        async with aiohttp.ClientSession() as session:
            params = {'key': key, 'params': params}
            async with session.post(self.p(self.urls['cloudscript_run']), json=params,
                                    headers=self.get_headers_json()) as resp:
                return await resp.json()

    async def upsert(self, model, data, let_null=False):
        query = self.query_builder_to_insert(data, let_null).set_model(model).compile()
        return await self.__then(query, self.is_update(data))

    async def __then(self, query_compiled, update):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    self.p(self.urls['row'] if not update else self.urls['update']), json=query_compiled,
                    headers=self.get_headers_json()) as resp:
                return await resp.json()

    '''
    ======================================
    Callback Functions
    ======================================
    '''

    def loginCallback(self, login, password, domain, call):
        self.make_callback(self.login(login, password, domain), call)

    def upsertCallback(self, model, data, call, let_null=False):
        self.make_callback(self.upsert(model, data, let_null), call)

    def make_callback(self, coroutine, call):
        try:
            if self.loop is None:
                raise Exception('SbxCore must initialize with manage_loop True')
            else:
                # future = asyncio.ensure_future(
                #    coroutine, loop=self.loop)
                def callback(fut):
                    call(None, fut.result())

                # future.add_done_callback(callback)

                future = asyncio.run_coroutine_threadsafe(coroutine, loop=self.loop)
                future.add_done_callback(callback)
        except Exception as inst:
            call(inst, None)

    def close_connection(self):
        if self.loop is not None:
            if self.loop.is_running():
                asyncio.gather(*asyncio.all_tasks()).cancel()
                self.loop.stop()
