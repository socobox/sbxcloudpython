class QueryBuilder:
    '''
    .. class:: QueryBuilder
       :platform: Unix, Windows
       :synopsis:  This is the main class uses to create the json params in order to do a find and delete request.
    .. moduleauthor:: Luis Guzman <lgguzman890414@gmail.com>
    '''
    def __init__(self):
        self.q = {"page": 1, "size": 1000, "where": []}
        self.group = {
            "ANDOR": "AND",
            "GROUP": []
        }
        self.OP = ["in", "IN", "not in", "NOT IN", "is", "IS", "is not", "IS NOT", "<>", "!=", "=", "<", "<=", ">=", ">",
              "like", "LIKE"]

    def set_domain(self, domain_id):
        self.q['domain'] = domain_id
        return self

    def set_model(self, model_name):
        self.q['row_model'] = model_name
        return self

    def set_page(self, page):
        self.q['page'] = page
        return self

    def set_page_size(self, page_size):
        self.q['size'] = page_size
        return self

    def order_by(self, field, asc):
        if asc is None:
            asc = False
        self.q['order_by'] = {'ASC': asc, 'FIELD': field}
        return self

    def fetch_models(self, array_of_model_names):
        self.q['fetch'] = array_of_model_names
        return self

    def reverse_fetch(self, array_of_model_names):
        self.q['rev_fetch'] = array_of_model_names
        return self

    def add_object_array(self, array):
        if 'where'  in self.q:
            del self.q['where']
        if 'rows' not in self.q:
            self.q['rows'] = []
        self.q['rows'] = self.q['rows'] + array
        return self

    def add_object(self, object):
        if 'where' in self.q:
            del self.q['where']
        if 'rows' not in self.q:
            self.q['rows'] = []
        self.q['rows'].append(object)
        return self

    def where_with_keys(self, keys_array):
        self.q['where'] = {"keys": keys_array}
        return self

    def new_group(self, connector_AND_or_OR):
        if 'rows' in self.q:
            del self.q['rows']
        if len(self.group['GROUP']) > 0:
            self.q['where'].append(self.group)
        self.group ={
                "ANDOR": connector_AND_or_OR,
                "GROUP": []
                }
        return self

    def set_reference_join(self, operator, filter_field, reference_field, model, value):
        self.q["reference_join"] = {
             "row_model": model,
             "filter": {
                 "OP": operator,
                 "VAL": value,
                 "FIELD": filter_field
             },
             "reference_field": reference_field
        }
        return self

    def add_condition(self, connector_AND_or_OR, field_name, operator, value):
        if len(self.group['GROUP'])  < 1:
            connector_AND_or_OR = "AND"
        self.group['GROUP'].append({
            "ANDOR": connector_AND_or_OR,
            "FIELD": field_name,
            "OP": operator,
            "VAL": value
        })

        return self

    def compile(self):
        if 'where' in self.q:
            if 'rows' in self.q:
                del self.q['rows']
            if isinstance(self.q['where'], list) and len(self.group['GROUP']) > 0:
                self.q['where'].append(self.group)

        elif 'rows' in self.q:
            if 'where' in self.q:
                del self.q['where']

            if 'order_by' in self.q:
                del self.q['order_by']

        return self.q

