	function setAlloweds_viewer(div_id,id){
			api.ajax('/isard-admin/alloweds/table/domains','POST',{'pk':id}).done(function(alloweds) {
                var all=false;
                $.each(alloweds,function(key, value) 
                {
                    if(typeof value !== 'undefined' && value.length == 0){all=true;}
                });
                if(all){
                    $(div_id+" #table-alloweds-"+id).append('<tr><td>Everyone</td><td>Has access</td></tr>');
                }else{
                    $.each(alloweds,function(key, value) 
                    {   
                        if(value){
			    var values=[];
			    value.forEach(function(data)
			    {
				values.push(data.name);
			    });			    
			    $(div_id+" #table-alloweds-"+id).append('<tr><td>'+key+'</td><td>'+values.join(', ')+'</td></tr>');
                        }

                    });
                }
			}); 
	}

	function replaceAlloweds_arrays(parent_id,data){
        if(!$(parent_id+' #a-roles-cb').length ){
            data['allowed']={   'groups':parseAllowed(parent_id,'a-groups'),
                                'users':parseAllowed(parent_id,'a-users')}
        }else{
            data['allowed']={'roles':    parseAllowed(parent_id,'a-roles'),
                            'categories':parseAllowed(parent_id,'a-categories'),
                            'groups':parseAllowed(parent_id,'a-groups'),
                            'users':parseAllowed(parent_id,'a-users')}
        }
        delete data['a-roles'];
        delete data['a-categories'];
        delete data['a-groups'];
        delete data['a-users'];
        delete data['a-roles-cb'];
        delete data['a-categories-cb'];
        delete data['a-groups-cb'];
        delete data['a-users-cb'];        
        return data
    }

    function parseAllowed(parent_id,id){
        d=$(parent_id+" #"+id).select2("val")
        if(d==null){
            if($(parent_id+' #'+id+'-cb').iCheck('update')[0].checked){
                return [];
            }
            return false
        }
        return d
    }
	

	function setAlloweds_add(parentid){
		ids=['a-roles','a-categories','a-groups','a-users']
		$.each(ids,function(idx,id){
			// https://github.com/dargullin/icheck/issues/159
			$(parentid+' #'+id+'-cb').iCheck('uncheck').iCheck('update');
			 $(parentid+' #'+id+'-cb').on('ifChecked', function(event){
				  $(parentid+" #"+id).attr('disabled',false);
			 });
			 $(parentid+' #'+id+'-cb').on('ifUnchecked', function(event){
				  $(parentid+" #"+id).attr('disabled',true);
                  $(parentid+" #"+id).empty().trigger('change')
			 });
			 $(parentid+" #"+id).attr('disabled',true);
            if( id.replace('a-','') == 'groups'){
                $(parentid+" #"+id).select2({
                    placeholder: "Empty applies to all. Type at least 2 letters to search.",
                    minimumInputLength: 2,
                    multiple: true,
                    ajax: {
                        type: "POST",
                        url: '/isard-admin/alloweds/term/'+id.replace('a-',''),
                        dataType: 'json',
                        contentType: "application/json",
                        delay: 250,
                        data: function (params) {
                            return  JSON.stringify({
                                term: params.term,
                                pluck: ['id','name','parent_category']
                            });
                        },
                        processResults: function (data) {
                            return {
                                results: $.map(data, function (item, i) {
                                    return {
                                        text: '['+item['parent_category']+'] '+item.name,
                                        id: item.id
                                    }
                                })
                            };
                        }
                    },
                });
            } else if (id.replace('a-','') == 'users') {
                $(parentid+" #"+id).select2({
                    placeholder: "Empty applies to all. Type at least 2 letters to search.",
                    minimumInputLength: 2,
                    multiple: true,
                    ajax: {
                        type: "POST",
                        url: '/isard-admin/alloweds/term/'+id.replace('a-',''),
                        dataType: 'json',
                        contentType: "application/json",
                        delay: 250,
                        data: function (params) {
                            return  JSON.stringify({
                                term: params.term,
                                pluck: ['id','name']
                            });
                        },
                        processResults: function (data) {
                            return {
                                results: $.map(data, function (item, i) {
                                    return {
                                        text: item.name + '['+item['uid']+'] ',
                                        id: item.id
                                    }
                                })
                            };
                        }
                    },
                });	
            } else{
                $(parentid+" #"+id).select2({
                    placeholder: "Empty applies to all. Type at least 2 letters to search.",
                    minimumInputLength: 2,
                    multiple: true,
                    ajax: {
                        type: "POST",
                        url: '/isard-admin/alloweds/term/'+id.replace('a-',''),
                        dataType: 'json',
                        contentType: "application/json",
                        delay: 250,
                        data: function (params) {
                            return  JSON.stringify({
                                term: params.term,
                                pluck: ['id','name']
                            });
                        },
                        processResults: function (data) {
                            return {
                                results: $.map(data, function (item, i) {
                                    return {
                                        text: item.name,
                                        id: item.id
                                    }
                                })
                            };
                        }
                    },
                });	
            }            

		});
	
	}
    
    
    
    function modalAllowedsFormShow(table,data){
        $('#modalAlloweds #alloweds_name').html(data.name)
        $('#modalAllowedsForm #id').val(data.id);
        $('#modalAlloweds #alloweds_panel').show()
        $("#modalAllowedsForm")[0].reset();
        $('#modalAlloweds').modal({
            backdrop: 'static',
            keyboard: false
        }).modal('show');
        //~ $('#modalAllowedsForm').parsley();
        setAlloweds_add('#modalAlloweds #alloweds-add'); 
        api.ajax('/isard-admin/alloweds/table/'+table,'POST',{'pk':data.id,'allowed':data.allowed}).done(function(alloweds) {
            $.each(alloweds,function(key, value) 
            {   
                $("#modalAllowedsForm #alloweds-add #a-"+key).empty().trigger('change')
                if(value){
                    $("#modalAllowedsForm #alloweds-add #a-"+key).attr('disabled',false)
                    $('#modalAllowedsForm #alloweds-add #a-'+key+'-cb').iCheck('check');
                    value.forEach(function(data)
                    {  
                        if('parent_category' in data){                                
                            var newOption = new Option('['+data['parent_category']+'] '+data.name, data.id, true, true);
                        }else{
                            var newOption = new Option(data.name, data.id, true, true);
                        }
                        $("#modalAllowedsForm #alloweds-add #a-"+key).append(newOption).trigger('change');
                    });
                }

            });
        });


        socket.off('allowed_result');
        socket.on('allowed_result', function (data) {
            var data = JSON.parse(data);
            if(data.result){
                $("#modalAlloweds").modal('hide');       
            }
            new PNotify({
                    title: data.title,
                    text: data.text,
                    hide: true,
                    delay: 4000,
                    icon: 'fa fa-'+data.icon,
                    opacity: 1,
                    type: data.type
            });
        });	                    

        $("#modalAlloweds #send").off('click');
        $("#modalAlloweds #send").on('click', function(e){
                var form = $('#modalAllowedsForm');

                form.parsley().validate();

                if (form.parsley().isValid()){
                    data=$('#modalAllowedsForm').serializeObject();
                    data=replaceAlloweds_arrays('#modalAllowedsForm #alloweds-add',data)
                    data['table']=table
                    socket.emit('allowed_update',data)
                }

                

            });                    
    }




