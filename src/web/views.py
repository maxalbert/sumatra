from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views.generic import list_detail
from django import forms
from sumatra.recordstore.django_store import models
from sumatra.projects import load_simulation_project
from sumatra.datastore import get_data_store
import mimetypes

_project = load_simulation_project()
project_name = _project.name
del _project

class TagSearch(forms.Form):
    search = forms.CharField() 
    
class SimulationUpdateForm(forms.ModelForm):
    wide_textarea = forms.Textarea(attrs={'rows': 2, 'cols':80})
    reason = forms.CharField(required=False, widget=wide_textarea)
    outcome = forms.CharField(required=False, widget=wide_textarea)
    
    class Meta:
        model = models.SimulationRecord
        fields=('reason', 'outcome', 'tags')

def show_project(request):
    project = load_simulation_project()
    return render_to_response('project_detail.html', {'project': project})
   
def list_simulations(request):
    search_form = TagSearch()
    return list_detail.object_list(request,
                                   queryset=models.SimulationRecord.objects.all(),
                                   template_name="simulation_list.html",
                                   extra_context={
                                    'project_name': project_name,
                                    'search_form': search_form})  

def simulation_detail(request, id):
    record = models.SimulationRecord.objects.get(id=id)
    
    
    if request.method == 'POST':
        if request.POST.has_key('delete'):
            record.delete()
            return HttpResponseRedirect('/')
        else:
            form = SimulationUpdateForm(request.POST, instance=record)
            if form.is_valid():
                form.save()
    else:
        form = SimulationUpdateForm(instance=record)
    data_store = get_data_store(record.datastore.type, eval(record.datastore.parameters))
    datafiles = data_store.list_files(record.data_key)
    assert isinstance(datafiles, list), type(datafiles)
    parameter_set = record.parameters.to_sumatra()    
    return render_to_response('simulation_detail.html', {'record': record,
                                                         'project_name': project_name,
                                                         'parameters': parameter_set.as_dict(),
                                                         'datafiles': datafiles,
                                                         'form': form
                                                         })

def delete_records(request):
    records_to_delete = request.POST.getlist('delete')
    records = models.SimulationRecord.objects.filter(id__in=records_to_delete)
    for record in records:
        record.delete()
    return HttpResponseRedirect('/')  
    

MAX_DISPLAY_LENGTH = 10*1024

def show_file(request, id):
    path = request.GET['path']
    
    record = models.SimulationRecord.objects.get(id=id)
    data_store = get_data_store(record.datastore.type, eval(record.datastore.parameters))
    # check the file is in the store for a given simulation
        
    try:
        mimetype, encoding = mimetypes.guess_type(path)
        if mimetype == None or mimetype.split("/")[0] == "text":
            content = data_store.get_content(record.data_key, path, max_length=MAX_DISPLAY_LENGTH)
            truncated = False
            if len(content) >= MAX_DISPLAY_LENGTH:
                truncated = True
            return render_to_response("show_file.html",
                                      {'path': path, 'id': id,
                                       'project_name': project_name,
                                       'content': content,
                                       'truncated': truncated,
                                       })
        elif mimetype in ("image/png", "image/jpeg", "image/gif"):
            return render_to_response("show_image.html",
                                      {'path': path, 'id': id,
                                       'project_name': project_name,})
        #elif mimetype == 'application/zip':
        #    import zipfile
        #    if zipfile.is_zipfile(path):
        #        zf = zipfile.ZipFile(path, 'r')
        #        contents = zf.namelist()
        #        zf.close()
        #        return render_to_response("show_file.html",
        #                              {'path': path, 'id': id,
        #                               'content': "\n".join(contents)
        #                               })
        #    else:
        #        raise IOError("Not a valid zip file")
        else:
            return render_to_response("show_file.html", {'path': path, 'id': id,
                                                         'project_name': project_name,
                                                         'content': "Can't display this file (mimetype assumed to be %s)" % mimetype})
    except IOError, e:
        return render_to_response("show_file.html", {'path': path, 'id': id,
                                                     'project_name': project_name,
                                                     'content': "File not found.",
                                                     'errmsg': e})
    
def show_image(request, id):
    path = request.GET['path']
    mimetype, encoding = mimetypes.guess_type(path)
    if mimetype in ("image/png", "image/jpeg", "image/gif"):
        record = models.SimulationRecord.objects.get(id=id)
        data_store = get_data_store(record.datastore.type, eval(record.datastore.parameters))
        content = data_store.get_content(record.data_key, path)
        response = HttpResponse(mimetype=mimetype)
        response.write(content)
        return response
    else:
        return HttpResponse(mimetype="image/png") # should return a placeholder image?