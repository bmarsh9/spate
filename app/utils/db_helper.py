#// Provides helper classes for the database models stored in models.py
from flask import session,current_app
from collections import namedtuple
from sqlalchemy import func, exc
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy import Integer
from app.utils.misc import msg_to_json
from app.utils.misc import get_table_object
from app.utils.misc import get_TableSchema
import parsedatetime as pdt
import random,colorsys
import json
from app import db
import sys

cal = pdt.Calendar()

#// ------------------------------------------------------ Dynamic Query Helper ------------------------------------------------------
class DynamicQuery():
    '''
    .Description: Helper function to generate queries in sqlalchemy
    .Example:
        query = DynamicQuery(
            model_class="Blacklist", --> databaseClass (M)
            request_args=[], --> parse request.args for parameters (from a uri string)
            filter=[("id", 'eq', 1),("datatype", 'eq', "path"),("date_added","gt","2018-05-10 02:05:57.1913")], --> filter to apply
            groupby=[("datatype","count"),("datavalue","group")], --> groupby fields
            orderby=("id","desc"),
            distinct="fieldname",
            getfirst=False, --> return the first record, a lot faster than sorting and limiting on large datasets
            getcount=False, --> return the count record
            as_query=False, --> return the raw query
            as_object=False, --> return the results as an object
            as_json=False, --> return the results as JSON
            as_datatables=False, --> return the results in datatables form
            as_chartjs=False, --> return the results in chartjs form
            as_schema=False, --> return the schema of a table
            concat=False --> Concatenate data fields; Only used for ChartJS. If using >1 group, there will be multiple keys ({"key":"name","otherkey":"name2","count":100}). ChartJS expects {"key":"name","count":100}. Otherwise use exc_fields to limit fields
            crud=action, --> perform CRUD ops
            data=data, --> data to be used for CRUD (dictionary required, collect with: "data=request.get_json(silent=True)" )
            qjson=data, --> send a query formatted as json (dictionary required, collect with: "qjson=request.get_json(silent=True)" ) # BETA
            inc_fields=["username","id"], --> fields to include in the response
            exc_fields=["password"], --> fields to exclude in the response
            visible="id,host_name", --> only used with as_datatables. Makes specific columns visible on load
            limit=5, --> limit the results
            orlist=["id";"1234","6789"] --> or query, zero index if the field, separated by ";" and the remaining indices are the matches (only runs as "eq" currently)
        )
        query.generate().all()
    '''
    def __init__(self, model, request_args=[], filter=[], groupby=[], orderby=(), distinct=None, inc_fields=[], exc_fields=[],visible=[],avg=False,sum=False,max=False,min=False,
        data={}, qjson={},getfirst=False, getcount=False, as_query=False, as_json=False,as_object=True, as_datatables=False, as_chartjs=False, as_schema=False, orlist=None,concat=None,crud=None, limit=10, reset_count=False,reverse_map=False,**kwargs):
        '''
        .Description --> Initialize variables, model is required
        '''
        self.request_args = request_args
        self.filter = filter
        self.groupby = groupby
        self.orderby = orderby
        self.avg = avg
        self.sum = sum
        self.max = max
        self.min = min
        self.distinct = distinct
        self.getfirst = getfirst
        self.getcount = getcount
        self.crud = crud
        self.concat = concat
        self.data = data
        self.qjson = qjson
        self.inc_fields = inc_fields
        self.visible = visible
        self.exc_fields = exc_fields + current_app.config["RESTRICTED_FIELDS"]
        self.as_query = as_query
        self.as_object = as_object
        self.as_json = as_json
        self.as_datatables = as_datatables
        self.as_chartjs = as_chartjs
        self.as_schema = as_schema
        self.reset_count = reset_count
        self.limit = limit
        self.orlist = orlist
        self.reverse_map = reverse_map

        self.py_version = sys.version_info

        #// Parse request.args from uri string
        if request_args:
            self.parse_uri(request_args)

        #// If grouping fields, get key names
        if self.groupby:
            if self.py_version < (3,0):
                key_names = dict(self.groupby).keys() #python2
            key_names=[]
            for c in self.groupby:
                key_names.append(c[0])
            key_names.insert(0,"count") # insert count at beginning (every groupby will yield a count)
            self.groupby_cols = key_names

        #// Get Database Model
        self.model = get_table_object(model)

    def getelement(self, li, index, default=None):
        '''
        .Description --> Easily get a list element
        '''
        try:
            return li[index]
        except IndexError:
            return default

    def str2bool(self,v):
        '''
        .Description --> Convert string to bool
        .data --> str2bool("true")
        '''
        return str(v).lower() in ("true")

    def parse_uri(self,request):
        '''
        .Description --> Parse request.args and turn into usable parameters.
            Any parameters set explicitly in DynamicQuery() will override request.args
        '''
        for key,value in request.items():
#            if key == "filter" and value and not self.filter: #old
#            self.filter = manually set
            if key == "filter" and value:
                hard_key = []
                for keyname in self.filter:
                    hard_key.append(keyname[0])
                filter_list = []
                for tup in value.split(";"):
                    keyname = tup.split(",")[0]
                    if keyname not in hard_key:
                        filter_list.append(tuple(tup.split(",")))
                self.filter = filter_list

            elif key == "groupby" and value and not self.groupby:
                group_list = []
                for tup in value.split(";"):
                    group_list.append(tuple(tup.split(",")))
                self.groupby = group_list
            elif key == "orderby" and value and not self.orderby:
                self.orderby = tuple(value.split(","))
            elif key == "avg" and value and not self.avg:
                self.avg = value
            elif key == "sum" and value and not self.sum:
                self.sum = value
            elif key == "max" and value and not self.max:
                self.max = value
            elif key == "min" and value and not self.min:
                self.min = value
            elif key == "distinct" and value and not self.distinct:
                self.distinct = tuple(value.split(","))
            elif key == "getfirst" and value and not self.getfirst:
                self.getfirst = self.str2bool(value)
            elif key == "getcount" and value and not self.getcount:
                self.getcount = self.str2bool(value)
            elif key == "inc_fields" and value and not self.inc_fields:
                self.inc_fields = value.split(",")
            elif key == "visible" and value and not self.visible:
                self.visible = tuple(value.split(","))
            elif key == "exc_fields" and value:
                self.exc_fields = value.split(",")+self.exc_fields
            elif key == "limit" and value != 10:
                self.limit = value
            elif key == "as_datatables" and value and not self.as_datatables:
                self.as_datatables = self.str2bool(value)
            elif key == "as_chartjs" and value and not self.as_chartjs:
                self.as_chartjs = self.str2bool(value)
            elif key == "as_object" and value and not self.as_object:
                self.as_object = self.str2bool(value)
            elif key == "as_json" and value and not self.as_json:
                self.as_json = self.str2bool(value)
            elif key == "as_query" and value and not self.as_query:
                self.as_query = self.str2bool(value)
            elif key == "as_schema" and value and not self.as_schema:
                self.as_schema = self.str2bool(value)
            elif key == "crud" and value and not self.crud:
                self.crud = value
            elif key == "concat" and value and not self.concat:
                self.concat = value
            elif key == "reset_count" and value and not self.reset_count:
                self.reset_count = self.str2bool(value)
            elif key == "orlist" and value and not self.orlist:
                t_orlist = value.split(";")
                or_list_values = t_orlist[1:][0].split(",")
                self.orlist = [t_orlist[0],or_list_values]
            elif key == "reverse_map" and value and not self.reverse_map:
                self.reverse_map = self.str2bool(value)

    def filter_fields(self, data):
        '''
        .Description --> Cut down dictionary based on Include/Exclude and Restricted fields names
        .data -> [{},{}]
        '''
        if not isinstance(data,list):
            data = [data]
        dataset = []
        if self.groupby: #// data is list of tuples
            for tup in data:
                temp_dic = {}
                for count,field in enumerate(tup):
                    key = self.groupby_cols[count]
                    if key == "count" and self.reset_count:
                        field = 1
                    if key not in self.exc_fields:
                        temp_dic[key] = str(field)
                dataset.append(temp_dic)
        else:
          for record in data: #// data is a sqlalchemy object
            temp_dict = {}
            #record.__dict__.pop("_sa_instance_state",None)
            del record.__dict__["_sa_instance_state"]
            for key,value in record.__dict__.items():
                if key not in self.exc_fields:
                    if not self.inc_fields:
                        temp_dict[key] = value
                    elif key in self.inc_fields:
                        temp_dict[key] = value
            dataset.append(temp_dict)
        return dataset

    def parse_groupby(self):
        '''
        .Description --> Filter for groupby queries
        .data -> [(),()]
        '''
        base_fields = [] #// base fields
        group_fields = [] #// group_by fields
        count_func = []
        for tup in self.groupby:
            field ,op = tup
            attr = getattr(self.model,field)
            if "count" in op:
                base_fields.append(func.count(attr))
            group_fields.append(attr)
            base_fields.append(attr)
        return base_fields,group_fields

    def parse_orderby(self,data): #// State: currently sqlalchemy orderby is used instead
        '''
        .Description --> Filter for orderby queries
        .data -> [{},{}]
        '''
        sort_field = self.getelement(self.orderby, 0, None)
        sort_type = self.getelement(self.orderby, 1, None)
        reverse = {"reverse":False}

        if sort_type == "desc":
            reverse["reverse"] = True
        if any(sort_field in d for d in data):
            data = sorted(data, key=lambda k: k[sort_field],**reverse)
        return data

    def to_schema(self):
        '''
        .Description --> Return the columns a table
        '''
        col_list = []
        for col in self.model.__table__.columns:
            if col.key not in self.exc_fields:
                if not self.inc_fields:
                    col_list.append(str(col.key))
                elif col.key in self.inc_fields:
                    col_list.append(str(col.key))
        return col_list

    def to_object(self,data):
        '''
        .Description --> Turn data into object
        .data -> [{},{}]
        '''
        dataset = {"data":[],"count":0}
        #if not isinstance(data,list):
        #    data = [data]
        for record in data:
            dataset["count"] += 1
            dataset["data"].append(namedtuple("Data", record.keys())(*record.values()))
        return dataset

    def to_datatables(self,data):
        '''
        .Description --> Turn data into datatables graph format
        .data -> [{},{}]
        '''
        data_dict = {"draw":0,"data": [],"count":0,"columns":[],"hide":[],"map":{}}
        if not isinstance(data,list):
            data = [data]
        for record in data:
            data_dict["count"] += 1
            temp_list = []
            if self.groupby:
                include_fields = self.groupby_cols
            elif self.inc_fields:
                include_fields = self.inc_fields
            else:
                include_fields = self.to_schema()
            for index_order,field in enumerate(include_fields):
                try:
                    temp_list.append(record[field])
                    if field not in data_dict["columns"]:
                        data_dict["columns"].append(field)
                        if self.reverse_map:
                            data_dict["map"][index_order] = field
                        else:
                            data_dict["map"][field] = index_order
                        if self.visible:
                            if field not in self.visible: # hide field on load
                                index = data_dict["columns"].index(field)
                                data_dict["hide"].append({"targets":[index],"visible":False})
                except KeyError:
                    print("key: {%s} does not exist or restricted" % (field))
            data_dict["data"].append(temp_list)
        return data_dict

    def to_chartjs(self,data):
        '''
        .Description --> Turn data into chartjs graph format
        .Depends on groupby (mostly)
        .data -> [{},{}]
        '''
        dataset = {"count":0, "label":[], "data": [], "color": []}
        if not isinstance(data,list):
            data = [data]
        for record in data:
            h,s,l = random.random(), 0.3 + random.random()/2.0, 0.4 + random.random()/5.0
            r,g,b = [int(256*i) for i in colorsys.hls_to_rgb(h,l,s)]
            color = "rgb(%s,%s,%s)" % (r,g,b)
            dataset["color"].append(color)
            dataset["count"] += 1
            if "count" not in record:
                dataset["warning"] = "Chartjs serialization requires the grouby parameter"
            temp_str = ""
            for k,v in record.items():
                if k == "count":
                    dataset["data"].append(v)
                else:
                    if self.concat:
                        temp_str+="{}->".format(v)
                    else:
                        dataset["label"].append(v)
            if temp_str:
                dataset["label"].append(temp_str[:-2])
        return dataset

    def to_crud(self,query,action=None):
        '''
        .Description --> Perform CRUD operation
        '''
        if action is None:
            action = self.crud
        crud_list = ["insert","update","delete"]
        if action in crud_list:
          try:
            #cols = self.to_schema()

            if action == "insert":
                record = self.model(**self.data)
                db.session.add(record)
                if self.as_query:
                    return query
                db.session.commit()
                return msg_to_json("Insert Success.",True,"success",id=record.id)

            elif action == "update":
                if self.data:
                    #// insert if it doesnt exist yet
                    exists = query.first()
                    if not exists:
                        return self.to_crud(query,action="insert")
                     # Check if columns exist, safer but slow
#                    for k,v in self.data.items():
#                        if k not in cols:
#                            return msg_to_json("Invalid column data.")
                    query = query.update(self.data)
                    if self.as_query:
                        return query
                    db.session.commit()
                    if query is 1:
                        return msg_to_json("Update Success.",True,"success")
                    return msg_to_json("No data was updated.",True,"success")
                return msg_to_json("Missing column data.")

            elif action == "delete":
                query = query.delete()
                if self.as_query:
                    return query
                db.session.commit()
                if query is 1:
                    return msg_to_json("Delete Success.",True,"success")
                return msg_to_json("No data was deleted.")

          except exc.IntegrityError:
              return msg_to_json("Integrity error. Record exists.")
          except Exception as e:
              print("Exception: %s" % str(e))
          finally:
              db.session.rollback()
              db.session.close()

        return msg_to_json("Invalid CRUD operation.")

    def filter_ops(self, filter_condition):
        '''
        Return filtered queryset based on condition.
        :param query: takes query
        :param filter_condition: Its a list, ie: [(key,operator,value)]
        operator list:
            ne for !=
            eq for ==
            lt for <
            ge for >=
            in for in_
            like for like
            value could be list or a string
        :return: queryset
        '''
        if self.groupby: #// Apply any grouping
                base_fields,group_fields = self.parse_groupby()
                __query = db.session.query(*base_fields)
                __query = __query.group_by(*group_fields)
        else:
            __query = db.session.query(self.model)

        if self.distinct:
            for each in self.distinct:
                __query = __query.distinct(getattr(self.model,each))

        if self.orlist:
            __query = __query.filter(or_(getattr(self.model,self.orlist[0]) == v for v in self.orlist[1]))

        for raw in filter_condition:
            try:
                key, op, value = raw
                if isinstance(value,str):
                    value = value.replace("*","%")
            except ValueError:
                raise Exception('Invalid filter: %s' % raw)

            if get_TableSchema(self.model,column=key,is_date=True) is True: # convert datetime field with parsedt
                value, result = cal.parseDT(str(value))

            column = getattr(self.model, key.lower(), None)
            if not column:
                raise Exception('Invalid filter column: %s' % key)
            if op == 'in':
                if isinstance(value, list):
                    filt = column.in_(value)
                else:
                    filt = column.in_(value.split(','))
            if op == 'nlike':
                filt = ~column.ilike(value)
#            elif op == 'not':
#                if isinstance(value, list):
#                    filt = column.not_(value)
#                else:
#                    filt = column.not_(value.split(','))
            else:
                try:
                    attr = list(filter(lambda e: hasattr(column, e % op), ['%s', '%s_', '__%s__']))[0] % op
                except IndexError:
                    raise Exception('Invalid filter operator: %s' % op)
                if value == 'null':
                    value = None
                filt = getattr(column, attr)(value)
            __query = __query.filter(filt)
        if self.orderby:
            sort_field = self.getelement(self.orderby, 0, None)
            sort_type = self.getelement(self.orderby, 1, None)
            if sort_type == "desc":
                q = getattr(self.model,sort_field).desc()
            elif sort_type == "asc":
                q = getattr(self.model,sort_field).asc()
            __query = __query.order_by(q)
#        if True: #// must include fields from orderby
#            __query = __query.distinct(getattr(self.model,"id"))
#            __query = __query.distinct(getattr(self.model,"cmd"))

        #// Query on JSON fields
        if self.qjson:
            __query = self.json_query(__query)
        return __query

    def json_query(self,queryobj):
        '''
        :Description - Query for data in JSON format (can query fields stored in JSON and `indexed` fields as well)
        :For JSON fields - Need to specifiy string in `subkeys`
        :For indexed fields - Leave `subkeys` as a empty array
        :Usage - {"query": {
                     "or_": [
                       {"column":"data","subkeys":["category"],"op":"eq","value":"win32_computersystemA"}, # will search column with JSON
                       {"column":"id","subkeys":[],"op":"eq","value":"indexed field"}, # will search indexed column
                     ],
                     "must_":[
                       {"column":"data","subkeys":["category"],"op":"eq","value":"win32_computersystemcoB"},
                     ],
                     "not_": [
                       {"column":"data","subkeys":["category"],"op":"eq","value":"win32_computersystemcoB"},
                     ]
                   }
                 }
        '''
        list_map = {
            "or_":{"args":[],"op":or_},
            "must_":{"args":[],"op":and_},
            "not_":{"args":[],"op":not_}
        }
        query = queryobj
        if not self.qjson: #// If there is not a query object request, return.
            return query
        try:
            for op_list,queries in self.qjson.get("query",None).items():
                if queries:
                    for data in queries:
                        try:
                            column = data["column"]
                            subkeys = data.get("subkeys",None)
                            op = data.get("op","eq")
                            value = data["value"]
                        except ValueError:
                            raise Exception('Invalid filter. Column and Value are mandatory.')

                        filt = getattr(self.model, column, None)
                        if not filt:
                            raise Exception('Invalid filter column: %s' % column)

                        if subkeys:
                            filt = filt[(subkeys)].astext
                            if isinstance(value, int):
                                filt = filt.cast(Integer)

                        if op == 'in':
                            if isinstance(value, list):
                                filt = filt.in_(value)
                            else:
                                filt = filt.in_(value.split(','))
                        else:
                            try:
                                attr = list(filter(lambda e: hasattr(filt, e % op), ['%s', '%s_', '__%s__']))[0] % op
                            except IndexError:
                                raise Exception('Invalid filter operator: %s' % op)

                            filt = getattr(filt, attr)(value)

                        list_map[op_list]["args"].append(filt)

            #// Add or_,not_,and_ to the query
            if list_map["not_"]["args"]:
                for each_not in list_map["not_"]["args"]:
                    query = query.filter(not_(each_not))

            query = query.filter(
                or_(
                    and_(
                        *list_map["must_"]["args"]
                    ),
                    *list_map["or_"]["args"]
                ),
            )
            # Backup
            #for op, attr in list_map.items():
            #    if attr["args"]:
            #        query = query.filter(attr["op"](*attr["args"]))

        except Exception as e:
            print(str(e))
        finally:
            return query

    def generate(self):
        '''
        .Description --> Generate a query and CRUD ops
        .data -> [{},{}]
        '''
        try:
            dataset = []

            if not self.model:
                raise Exception("Database Model does not exist.")

            #// Return schema of table
            if self.as_schema:
                return self.to_schema()

            #// Filter query by sending to filter_ops functions
            query = self.filter_ops(self.filter)

            #// CRUD Operations
            if self.crud is not None:
                return self.to_crud(query)

            t_count = query.count()
            #// Set record limit
            if self.limit:
                query = query.limit(self.limit)

            #// Return query
            if self.as_query is True:
                return query

            if self.avg:
                val = query.with_entities(func.avg(getattr(self.model,self.avg.lower())).label("average")).first()[0]
                return {"average":round(val,1)}

            elif self.sum:
            val = query.with_entities(func.sum(getattr(self.model,self.sum.lower())).label("sum")).first()[0]
                return {"sum":round(val,1)}

            elif self.max:
                val = query.with_entities(func.max(getattr(self.model,self.max.lower())).label("sum")).first()[0]
                return {"max":round(val,1)}

            elif self.min:
                val = query.with_entities(func.min(getattr(self.model,self.min.lower())).label("sum")).first()[0]
                return {"min":round(val,1)}

            #// Return data (with filter applied)
            else:
                #// Return count
                if self.getcount is True:
                    data_dict = {"data": [],"count":int(t_count),"total":int(t_count)}
                    return data_dict
                #// One record
                elif self.getfirst is True:
                    raw_data = query.first()
                else: #// Get all
                    raw_data = query.all()

                if raw_data:
                    data = self.filter_fields(raw_data)
#                if self.orderby:
#                    data = self.parse_orderby(data)

                    #// Specify the format
                    if self.as_datatables:
                        dataset = self.to_datatables(data)
                    elif self.as_chartjs:
                        dataset = self.to_chartjs(data)
                    elif self.as_json:
                        dataset = {"count":int(query.count()), "data": data}
                    else:
                        dataset = self.to_object(data)
                if not dataset:
                    dataset = {"data": [],"count":0}
#                dataset["total"] = int(query.count())
                dataset["total"] = int(t_count)
                return dataset
        except Exception as e:
            print("db_helper: Caught unexpected exception. Error:{}".format(e))
            return msg_to_json(e)
