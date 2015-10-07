from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser, FormParser
from storlet.models import Storlet, Dependency, StorletUser, DependencyUser
from storlet.serializers import StorletSerializer, DependencySerializer, StorletUserSerializer, DependencyUserSerializer
from swiftclient import client as c
from rest_framework.views import APIView
from django.conf import settings
import redis
# Create your views here.
r = redis.StrictRedis(host='localhost', port=6379, db=0)
class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

def is_valid_request(request):
    headers = {}
    try:
        headers['X-Auth-Token'] = request.META['HTTP_X_AUTH_TOKEN']
        return headers
    except:
        return None

class StorletList(APIView):
    """
    List all storlets, or create a new storlet.
    """
    def get(self, request, format=None):
        storlets = Storlet.objects.all()
        serializer = StorletSerializer(storlets, many=True)
        return JSONResponse(serializer.data)

    def post(self, request, format=None):
        data = JSONParser().parse(request)
        serializer = StorletSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

@csrf_exempt
def storlet_detail(request, id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'GET':
        serializer = StorletSerializer(storlet)
        return JSONResponse(serializer.data, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = StorletSerializer(storlet, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        storlet.delete()
        return JSONResponse('Storlet has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

class StorletData(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    def put(self, request, id, format=None):
        file_obj = request.FILES['file']
        path = save_file(file_obj, settings.STORLET_DIR)
        try:
            storlet = Storlet.objects.get(id=id)
            storlet.path = path
            storlet.save()
        except Storlet.DoesNotExist:
            return JSONResponse('Storlet does not exists', status=404)
        return JSONResponse('Storlet has been updated', status=201)
    def get(self, request, id, format=None):
        #TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)

@csrf_exempt
def storlet_deploy(request, id, account):
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return JSONResponse('Storlet does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        #TODO: add params in the request body
        params = JSONParser().parse(request)

        metadata = {'X-Object-Meta-Storlet-Language':'Java',
            'X-Object-Meta-Storlet-Interface-Version':'1.0',
            'X-Object-Meta-Storlet-Dependency': storlet.dependencies,
            'X-Object-Meta-Storlet-Object-Metadata':'no',
            'X-Object-Meta-Storlet-Main': storlet.main_class}
        f = open(storlet.path,'r')
        content_length = None
        response = dict()
        #Change to API Call
        try:
            c.put_object(settings.SWIFT_URL+"AUTH_"+str(account), headers["X-Auth-Token"], 'storlet', storlet.name, f,
                         content_length, None, None,
                         "application/octet-stream", metadata,
                         None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            f.close()
        status = response.get('status')
        if status == 201:
            if r.get("AUTH_"+str(account)):
                return JSONResponse("Already deployed", status=200)

            if r.lpush("AUTH_"+str(account), str(storlet.name)):
                if r.hmset("AUTH_"+str(account)+":"+str(storlet.name), params):
                    return JSONResponse("Deployed", status=201)

        return JSONResponse("error", status=400)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def storlet_list_deployed(request, account):
    if request.method == 'GET':
        result = r.lrange("AUTH_"+str(account), 0, -1)
        if result:
            return JSONResponse(result, status=200)
        else:
            return JSONResponse('Any Storlet deployed', status=404)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def storlet_undeploy(request, id, account):
    try:
        storlet = Storlet.objects.get(id=id)
    except Storlet.DoesNotExist:
        return JSONResponse('Storlet does not exists', status=404)

    if not r.hgetall("AUTH_"+str(account)+":"+str(storlet.name)):
        return JSONResponse('Filter '+str(storlet.name)+' has not been deployed already', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        try:
            c.delete_object(settings.SWIFT_URL+"AUTH_"+str(account),headers["X-Auth-Token"],
                'storlet', storlet.name, None, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        status = response.get('status')
        if 200 <= status < 300:
            r.lrem("AUTH_"+str(account), 1, str(storlet.name))
            return JSONResponse('The object has been deleted', status=status)
        return JSONResponse(response.get("reason"), status=status)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

"""
------------------------------
DEPENDENCY PART
------------------------------
"""
@csrf_exempt
def dependency_list(request):
    """
    List all dependencies, or create a Dependency.
    """
    if request.method == 'GET':
        dependencies = Dependency.objects.all()
        serializer = DependencySerializer(dependencies, many=True)
        return JSONResponse(serializer.data, status=202)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = DependencySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_detail(request, id):
    """
    Retrieve, update or delete a Dependency.
    """
    try:
        dependency = Dependency.objects.get(id=id)
    except Dependency.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'GET':
        serializer = DependencySerializer(dependency)
        return JSONResponse(serializer.data, status=200)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = DependencySerializer(dependency, data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        dependency.delete()
        return JSONResponse('Dependency with id:'+str(id)+'has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

class DependencyData(APIView):
    parser_classes = (MultiPartParser, FormParser,)
    def put(self, request, id, format=None):
        file_obj = request.FILES['file']
        path = save_file(file_obj, settings.DEPENDENCY_DIR)
        try:
            dependency = Dependency.objects.get(id=id)
            dependency.path = path
            dependency.save()
        except Dependency.DoesNotExist:
            return JSONResponse('Dependency does not exists', status=404)
        serializer = DependencySerializer(dependency)
        return JSONResponse(serializer.data, status=201)
    def get(self, request, id, format=None):
        #TODO Return the storlet data
        data = "File"
        return Response(data, status=None, template_name=None, headers=None, content_type=None)



@csrf_exempt
def dependency_deploy(request, id, account):
    try:
        dependency = Dependency.objects.get(id=id)
    except Dependency.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)

        metadata = {'X-Object-Meta-Storlet-Dependency-Version': str(dependency.version)}
        f = open(dependency.path,'r')
        content_length = None
        response = dict()
        try:
            c.put_object(settings.SWIFT_URL+"AUTH_"+str(account), headers["X-Auth-Token"], 'dependency', dependency.name, f,
                         content_length, None, None, "application/octet-stream",
                         metadata, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        finally:
            f.close()
        status = response.get('status')
        if 200 <= status < 300:
            try:
                #TODO: Control version, it's possible add call to updrade the version
                dependency_user = DependencyUser.objects.get(dependency=dependency, user_id=account)
                return JSONResponse("Already deployed", status=200)
            except DependencyUser.DoesNotExist:
                dependency_user = DependencyUser.objects.create(dependency_id=dependency.id, user_id=account)
                return JSONResponse("Deployed", status=201)
        return JSONResponse('ERROR',status=500)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_list_deployed(request, account):

    if request.method == 'GET':
        try:
            dependency = DependencyUser.objects.filter(user_id=account)
        except DependencyUser.DoesNotExist:
	           return JSONResponse('Any Dependency deployed', status=404)
        serializer = DependencyUserSerializer(dependency, many=True)
        return JSONResponse(serializer.data, status=200)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dependency_undeploy(request, id, account):
    try:
        dependency = Dependency.objects.get(id=id)
        dependency_user = DependencyUser.objects.get(dependency_id=dependency.id, user_id=account)
    except DependencyUser.DoesNotExist:
        return JSONResponse('Dependency '+str(id)+' has not been deployed', status=404)
    except Dependency.DoesNotExist:
        return JSONResponse('Dependency does not exists', status=404)

    if request.method == 'PUT':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        response = dict()
        try:
            c.delete_object(settings.SWIFT_URL+"AUTH_"+str(account),headers["X-Auth-Token"],
                'dependency', dependency.name, None, None, None, None, response)
        except:
            return JSONResponse(response.get("reason"), status=response.get('status'))
        status = response.get('status')
        if 200 <= status < 300:
            DependencyUser.objects.get(id=dependency_user.id).delete()
            return JSONResponse("The object has been deleted", status=status)
        return JSONResponse(response.get("reason"), status=status)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

def save_file(file, path=''):
    '''
    Little helper to save a file
    '''
    filename = file._get_name()
    fd = open(str(path) +"/"+ str(filename), 'wb')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()
    return str(path) +"/"+ str(filename)
