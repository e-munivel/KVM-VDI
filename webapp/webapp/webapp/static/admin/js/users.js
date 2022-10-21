/*
* Copyright 2017 the Isard-vdi project authors:
*      Josep Maria Viñolas Auquer
*      Alberto Larraz Dalmases
* License: AGPLv3
*/

var users_table= ''
var current_category = ''

$(document).ready(function() {
    $('.admin-status').show()
    $template = $(".template-detail-users");
    
	$('.btn-new-user').on('click', function () {
        setQuotaMax('#users-quota',kind='category',id=false,disabled=false);
        $('#modalAddUser').modal({backdrop: 'static', keyboard: false}).modal('show');
        $('#modalAddUserForm')[0].reset();

        $('#modalAddUserForm #secondary_groups').select2({
            minimumInputLength: 2,
            multiple: true,
            ajax: {
                type: "POST",
                url: '/api/v3/admin/alloweds/term/groups/',
                dataType: 'json',
                contentType: "application/json",
                delay: 250,
                data: function (params) {
                    return  JSON.stringify({
                        term: params.term,
                        category: current_category,
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

        setModalUser();
	});


    
	$('.btn-new-bulkusers').on('click', function () {
        $('#bulk-allow-update').iCheck('uncheck').iCheck('update');
        setQuotaMax('#bulkusers-quota',kind='category',id=false,disabled=false);
        $("#modalAddBulkUsers #send").attr("disabled", true);
        $('#modalAddBulkUsers').modal({backdrop: 'static', keyboard: false}).modal('show');
        $('#modalAddBulkUsersForm')[0].reset();
        if ( $.fn.dataTable.isDataTable( '#csv_preview' ) ) {
            csv_preview.clear().draw()
            $("#csv_correct").hide()
            $("#csv_error").hide()
        }
        setModalUser();

        $('#modalAddBulkUsersForm #bulk_secondary_groups').select2({
            minimumInputLength: 2,
            multiple: true,
            ajax: {
                type: "POST",
                url: '/api/v3/admin/alloweds/term/groups/',
                dataType: 'json',
                contentType: "application/json",
                delay: 250,
                data: function (params) {
                    return  JSON.stringify({
                        term: params.term,
                        category: current_category,
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
	});

    $('.btn-bulkdelete').on('click', function () {
        let usersToDelete = [];
            $.each(users_table.rows('.active').data(),function(key, value){
                usersToDelete.push(value);
            });        

        if (!(usersToDelete.length == 0)) {
            $("#modalDeleteUserForm")[0].reset();
            $('#modalDeleteUserForm #id').val(JSON.stringify(usersToDelete));
            $('#modalDeleteUser').modal({
                backdrop: 'static',
                keyboard: false
            }).modal('show');
            $.ajax({
                type: "POST",
                url: "/api/v3/admin/users/delete/check",
                data: JSON.stringify(usersToDelete),
                contentType: "application/json"
            }).done(function (domains) {
                $('#table_modal_delete tbody').empty()
                $.each(domains, function (key, value) {
                    infoDomains(value, $('#table_modal_delete tbody'));
                });
            });
        } else {
            new PNotify({
                text: "Please select the users you want to delete",
                hide: true,
                opacity: 1,
                delay: 1000
            });
        }
    });

	$('#btn-download-bulkusers').on('click', function () {
        var viewerFile = new Blob(["username,name,email,password,group,category,role\njdoe,John Doe,jdoe@isardvdi.com,sup3rs3cr3t,Default,Default,advanced\nauser,Another User,auser@domain.com,a1sera1ser,Default,Default,user"], {type: "text/csv"});
        var a = document.createElement('a');
            a.download = 'bulk-users-template.csv';
            a.href = window.URL.createObjectURL(viewerFile);
        var ev = document.createEvent("MouseEvents");
            ev.initMouseEvent("click", true, false, self, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
            a.dispatchEvent(ev);  
	});

    function filter_groups(category_select, group_select) {
        let category = category_select.val()
        group_select.find('option').each(function () {
            if (this.value.startsWith(category + "-")) {
                this.disabled = false
            } else {
                this.disabled = true
                if (this.selected) {
                    $(this).prop('selected', false)
                }
            }
        })
    }
    $("#add-category").on('change', function () {
        current_category = ($(this).val())
        filter_groups($(this), $('#add-group'))
        $("#secondary_groups").empty().trigger('change')
    })
    $("#bulk-category").on('change', function () {
        current_category = ($(this).val())
        filter_groups($(this), $('#bulk-group'))
        $("#secondary_groups").empty().trigger('change')
    })

    $("#modalAddUser #send").on('click', function(e){
        var form = $('#modalAddUserForm');
        formdata = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){   // || 'unlimited' in formdata){   
            data=userQuota2dict(formdata);
            data['password']=data['password-add-user'];
            delete data['password-add-user'];
            delete data['password2-add-user'];
            delete data['unlimited'];
            delete data['id'];
            data['provider']='local';
            data['bulk']=false;
            data['username']=$('#modalAddUserForm #id').val();
            var notice = new PNotify({
                text: 'Creating user...',
                hide: true,
                opacity: 1,
                icon: 'fa fa-spinner fa-pulse'
            })
            $.ajax({
                type: "POST",
                url:"/api/v3/admin/user" ,
                data: JSON.stringify(data),
                contentType: "application/json",
                error: function (data) {
                    notice.update({
                        title: "ERROR creating user",
                        text: data.responseJSON.description,
                        type: 'error',
                        hide: true,
                        icon: 'fa fa-warning',
                        delay: 15000,
                        opacity: 1
                    });
                },
                success: function(data)
                {
                    $('form').each(function() { this.reset() });
                    $('.modal').modal('hide');
                    notice.update({
                        title: "Created",
                        text: 'User created successfully',
                        hide: true,
                        delay: 2000,
                        icon: 'fa fa-' + data.icon,
                        opacity: 1,
                        type: 'success'
                    })
                }
            });
        }
    }); 

    $("#modalEditUser #send").on('click', function(e){
        var form = $('#modalEditUserForm');
        disabled = $('#modalEditUserForm').find(':input:disabled').removeAttr('disabled');
        formdata = form.serializeObject();
        disabled.attr('disabled', 'disabled');
        form.parsley().validate();
        if (form.parsley().isValid()){     // || 'unlimited' in formdata){   
            data=userQuota2dict(formdata);
            delete data['unlimited']
            var notice = new PNotify({
                text: 'Updating user...',
                hide: true,
                opacity: 1,
                icon: 'fa fa-spinner fa-pulse'
            })
            $.ajax({
                type: "PUT",
                url:"/api/v3/admin/user/" + data['id'],
                data: JSON.stringify(data),
                contentType: "application/json",
                error: function(data) {
                    notice.update({
                        title: 'ERROR Updating user',
                        text: data.responseJSON.description,
                        type: 'error',
                        hide: true,
                        icon: 'fa fa-warning',
                        delay: 5000,
                        opacity: 1
                    })
                },
                success: function(data)
                {
                    $('form').each(function() { this.reset() });
                    $('.modal').modal('hide');
                    notice.update({
                        title: 'Updated',
                        text: 'User updated successfully',
                        hide: true,
                        delay: 2000,
                        icon: 'fa fa-' + data.icon,
                        opacity: 1,
                        type: 'success'
                    })
                }
            });     
        }
    }); 

    $("#modalPasswdUser #send").on('click', function(e){
        var form = $('#modalPasswdUserForm');
        form.parsley().validate();
        if (form.parsley().isValid()){
            data={}
            data['id']=$('#modalPasswdUserForm #id').val();
            data['name']=$('#modalPasswdUserForm #name').val();
            data['password']=$('#modalPasswdUserForm #password-reset').val();
            $.ajax({
                type: "PUT",
                url:"/api/v3/admin/user/" + data['id'],
                data: JSON.stringify(data),
                contentType: "application/json",
                success: function(data)
                {
                    $('form').each(function() { this.reset() });
                    $('.modal').modal('hide');
                }
            }); 
        }
    });

    $('#modalDeleteUser #send').on('click', function(e) {
        user = $('#modalDeleteUserForm #id').val()

        var notice = new PNotify({
            text: 'Deleting user(s)...',
            hide: false,
            opacity: 1,
            icon: 'fa fa-spinner fa-pulse'
        })
        $('form').each(function() {
            this.reset()
        })
        $('.modal').modal('hide')
        $.ajax({
            type: 'DELETE',
            url: '/api/v3/admin/user',
            data: user,
            contentType: 'application/json',
            error: function(data) {
                notice.update({
                    title: 'ERROR',
                    text: data.responseJSON.description,
                    type: 'error',
                    hide: true,
                    icon: 'fa fa-warning',
                    delay: 5000,
                    opacity: 1
                })
            },
            success: function(data) {
                notice.update({
                    text: 'User(s) deleted successfully',
                    hide: true,
                    delay: 2000,
                    icon: '',
                    opacity: 1,
                    type: 'success'
                })
            }
        })
    });  

       document.getElementById('csv').addEventListener('change', readFile, false);
       var filecontents=''
       function readFile (evt) {
           var files = evt.target.files;
           var file = files[0];           
           var reader = new FileReader();
           reader.onload = function(event) {
             filecontents=event.target.result;
             csv2datatables(filecontents)
           }
           reader.readAsText(file, 'UTF-8')
        }

    $("#modalAddBulkUsers #send").on('click', function(e){
        var form = $('#modalAddBulkUsersForm');
        $("#modalAddBulkUserForm #bulk_secondary_groups").empty().trigger('change')
        formdata = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){
            data=userQuota2dict(formdata);
            delete data['unlimited']
            data['provider']='local';
            users=csv_preview.data().toArray()
            var notice = new PNotify({
                title: "Adding users",
            });
            var usersAdded = 1;
            users.forEach(function (user) {
                data['uid'] = user['username'];
                data['bulk'] = true
                if(user["exists"] && !$('#bulk-allow-update').prop("checked")){
                    notice.update({
                        title: "Adding users",
                        text: "Skipping user "+user["username"]+" as already exists",
                        hide: true,
                        delay: 4000,
                        opacity: 1
                    });
                    return true
                }

                if(user["exists"] && $('#bulk-allow-update').prop("checked")){
                    user['secondary_groups'] = data['secondary_groups']
                    $.ajax({
                        type: 'POST',
                        url: "/api/v3/admin/users/check/by/provider",
                        data: JSON.stringify({
                            "provider":data['provider'],
                            "category":user['category'],
                            "uid":user['username']
                        }),
                        contentType: "application/json",
                        success: function(data){
                            $.ajax({
                                type: 'PUT',
                                url: "/api/v3/admin/user/"+data,
                                data: JSON.stringify(user) ,
                                contentType: "application/json",
                                success: function(data)
                                {
                                    $('form').each(function() { this.reset() });
                                    $('.modal').modal('hide');
                                notice.update({
                                        title: "Updating users",
                                        text: "Updating user (" + ( usersAdded ) + "/" + users.length + "): ",
                                        hide: true,
                                        delay: 4000,
                                        opacity: 1
                                    });
                                usersAdded ++;
                                 },
                                 error: function(data){
                                    new PNotify({
                                        title: "ERROR updating user "+user.username,
                                        text: data.responseJSON.description,
                                        type: 'error',
                                        hide: true,
                                        icon: 'fa fa-warning',
                                        delay: 15000,
                                        opacity: 1
                                    });
                                 }
                            }); 


                        }
                    })
                }else{
                    delete user["exists"]
                    $.ajax({
                        type: 'POST',
                        url: "/api/v3/admin/user",
                        data: JSON.stringify(Object.assign({},data,user)) ,
                        contentType: "application/json",
                        success: function(data)
                        {
                            $('form').each(function() { this.reset() });
                            $('.modal').modal('hide');
                        notice.update({
                                title: "Adding users",
                                text: "Added user (" + ( usersAdded ) + "/" + users.length + "): ",
                                hide: true,
                                delay: 4000,
                                opacity: 1
                            });
                        usersAdded ++;
                        },
                        error: function(data){
                            new PNotify({
                                title: "ERROR adding user "+user.username,
                                text: data.responseJSON.description,
                                type: 'error',
                                hide: true,
                                icon: 'fa fa-warning',
                                delay: 15000,
                                opacity: 1
                            });
                        }
                    }); 
                }
            });
        }
    }); 

    $("#add-category").on('change', function(e){
        setQuotaMax('#users-quota',kind='category',id=$(this).val(),disabled=false);
        //setQuotaTableDefaults('#users-quota','categories',$(this).val())
    });
    $("#add-group").on('change', function(e){
        setQuotaMax('#users-quota',kind='group',id=$(this).val(),disabled=false);
        //setQuotaTableDefaults('#users-quota','groups',$(this).val())
    });

    $("#bulk-category").on('change', function(e){
        setQuotaMax('#bulkusers-quota',kind='category',id=$(this).val(),disabled=false);
        /* setQuotaTableDefaults('#bulkusers-quota','categories',$(this).val()) */
    });
    $("#bulk-group").on('change', function(e){
        setQuotaMax('#bulkusers-quota',kind='group',id=$(this).val(),disabled=false);
        /* setQuotaTableDefaults('#bulkusers-quota','groups',$(this).val()) */
    });


     $('#domains_tree input:checkbox').on('ifChecked', function(event){
        $(this).closest('div').next('ul').find('input:checkbox').iCheck('check').attr('disabled',true) //.prop('disabled',true);
     });
     $('#domains_tree input:checkbox').on('ifUnchecked', function(event){
          $(this).closest('div').next('ul').find('input:checkbox').iCheck('uncheck').attr('disabled',false)
     });        
            
    users_table=$('#users').DataTable( {
        "ajax": {
            "url": "/admin/users",
            "dataSrc": "",
            "type" : "GET",
            "data": function(d){return JSON.stringify({})}
        },
			"language": {
				"loadingRecords": '<i class="fa fa-spinner fa-pulse fa-3x fa-fw"></i><span class="sr-only">Loading...</span>'
        },
        "rowId": "id",
        "deferRender": true,
        "columns": [
				{
                "className":      'details-control',
                "orderable":      false,
                "data":           null,
                "width": "10px",
                "defaultContent": '<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
				},
            { "data": "active", "width": "10px"},
            { "data": "name"},
            { "data": "provider"},
            { "data": "category"},
            { "data": "uid"},
            { "data": "username"},
            { "data": "role", "width": "10px"},
            { "data": "group", "width": "10px"},
            { "data": "vpn.wireguard.connected", "width": "10px", "defaultContent": 'NaN'},
            //~ {
                //~ "data": null,
                //~ className: "center xe-password",
                //~ "defaultContent": '  \
                                //~ <div><i class="fa fa-lock"></i> \
                              //~ </div>'
            //~ },
            { "data": "accessed"},
            { "data": "templates", "width": "10px"},
            { "data": "desktops", "width": "10px"},
            {
                "className": 'select-checkbox',
                "data": null,
                "orderable": false,
                "width": "10px",
                "defaultContent": '<input type="checkbox" class="form-check-input"></input>'
            },],

			 "columnDefs": [
							{
							"targets": 1,
							"render": function ( data, type, full, meta ) {
                                    if(type === "display"){
                                        if(full.active==true){
                                            return '<i class="fa fa-check" style="color:lightgreen"></i>';
                                        }else{
                                            return '<i class="fa fa-close" style="color:darkgray"></i>';
                                        }
                                    }
                                    return data;
                            }},
                            {
                            "targets": 9,
                            "render": function ( data, type, full, meta ) {
                                if('vpn' in full && full['vpn']['wireguard']['connected']){
                                    return '<i class="fa fa-circle" aria-hidden="true"  style="color:green" title="'+full["vpn"]["wireguard"]["remote_ip"]+':'+full["vpn"]["wireguard"]["remote_port"]+'"></i>'
                                }else{
                                    return '<i class="fa fa-circle" aria-hidden="true"  style="color:darkgray"></i>'
                                }
                            }},
							{
							"targets":10,
							"render": function ( data, type, full, meta ) {
                                        return moment.unix(full.accessed).toISOString("YYYY-MM-DDTHH:mm:ssZ"); //moment.unix(full.accessed).fromNow();
                                        }}
             ]
        });
    //~ });

    users_table.on( 'click', 'tr[role="row"]', function (e) { 
        toggleRow(this, e);
     });

    $('#users').find('tbody').on('click', 'td.details-control', function () {
        var tr = $(this).closest('tr');
        var row = users_table.row( tr );

        if ( row.child.isShown() ) {
            row.child.hide();
            tr.removeClass('shown');
        }else {
            if ( users_table.row( '.shown' ).length ) {
                $('.details-control', users_table.row( '.shown' ).node()).click();
            }
            row.child(renderUsersDetailPannel(row.data())).show()
            actionsUserDetail()
            tr.addClass('shown');
            id = row.data().id
            setQuotaMax(
                '#show-users-quota-' + id,
                kind='user',
                id=id,
                disabled=true
            )
            setLimitsMax(
                '#show-users-limits-' + id,
                kind='user',
                id=id,
                disabled=true
            )
        }
    });



    socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port+'/administrators', {
        'query': {'jwt': localStorage.getItem("token")},
        'path': '/api/v3/socket.io/',
        'transports': ['websocket']
    });
     
    socket.on('connect', function() {
        connection_done();
        console.log('Listening users namespace');
    });

    socket.on('connect_error', function(data) {
      connection_lost();
    });

    socket.on('user_quota', function(data) {
        console.log('Quota update')
        var data = JSON.parse(data);
        drawUserQuota(data);
    });

    socket.on('users_data', function(data) {
        var data = JSON.parse(data);
        dtUpdateInsert(users_table,data,false);
        //var data = JSON.parse(data);
        //drawUserQuota(data);
    });

    socket.on('users_delete', function(data) {
        var data = JSON.parse(data);
        users_table.row('#'+data.id).remove().draw();
        //var data = JSON.parse(data);
        //drawUserQuota(data);
    });

    socket.on('add_form_result', function (data) {
        var data = JSON.parse(data);
        //if(data.result){
            $('form').each(function() { this.reset() });
            $('.modal').modal('hide');
            $('#modalAddBulkUsers #send').prop('disabled', false);
        //}
        new PNotify({
                title: data.title,
                text: data.text,
                hide: true,
                delay: 4000,
                icon: 'fa fa-'+data.icon,
                opacity: 1,
                type: data.type
        });
        users_table.ajax.reload()
    });

    socket.on ('result', function (data) {
        var data = JSON.parse(data);
        new PNotify({
                title: data.title,
                text: data.text,
                hide: true,
                delay: 4000,
                icon: 'fa fa-'+data.icon,
                opacity: 1,
                type: data.type
        });
        users_table.ajax.reload()
    });    
    
});


function actionsUserDetail(){
	$('.btn-edit').on('click', function () {            
            var pk=$(this).closest("div").attr("data-pk");
            $("#modalEditUserForm")[0].reset();
            $("#modalEditUserForm #secondary_groups").empty().trigger('change')
			$('#modalEditUser').modal({
				backdrop: 'static',
				keyboard: false
            }).modal('show');
            setModalUser();
            api.ajax('/api/v3/admin/table/users','POST',{'id':pk}).done(function(user) {
                $('#modalEditUserForm #name').val(user.name);
                $('#modalEditUserForm #id').val(user.id);
                $('#modalEditUserForm #uid').val(user.uid);
                $('#modalEditUserForm #email').val(user.email);
                $('#modalEditUserForm #role option:selected').prop("selected", false);
                $('#modalEditUserForm #role option[value="'+user.role+'"]').prop("selected",true);
                $('#modalEditUserForm #category option:selected').prop("selected", false);
                $('#modalEditUserForm #category option[value="'+user.category+'"]').prop("selected",true);
                current_category=user.category;
                $('#modalEditUserForm #group option:selected').prop("selected", false);
                $('#modalEditUserForm #group option[value="'+user.group+'"]').prop("selected",true);                
                $('#modalEditUserForm').parsley().validate();
                $.each(user.secondary_groups, function(i, group) {
                    var newOption = new Option(group, group, true, true);
                    $("#modalEditUserForm #secondary_groups").append(newOption).trigger('change');
                })
            });
            $('#modalEditUserForm #secondary_groups').select2({
                minimumInputLength: 2,
                multiple: true,
                ajax: {
                    type: "POST",
                    url: '/api/v3/admin/alloweds/term/groups/',
                    dataType: 'json',
                    contentType: "application/json",
                    delay: 250,
                    data: function (params) {
                        return  JSON.stringify({
                            term: params.term,
                            category: current_category,
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
            setQuotaMax('#edit-users-quota',kind='user',id=pk,disabled=false);
	});

	$('.btn-passwd').on('click', function () {
            var closest=$(this).closest("div");
            var pk=closest.attr("data-pk");
            var name=closest.attr("data-name");
            var username=closest.attr("data-username");
            $("#modalPasswdUserForm")[0].reset();
			$('#modalPasswdUser').modal({
				backdrop: 'static',
				keyboard: false
			}).modal('show');
            $('#modalPasswdUserForm #name').val(name);
            $('#modalPasswdUserForm #id').val(pk);
            $('#modalPasswdUserForm #username').val(username);
	});

    
	$('.btn-delete').on('click', function () {
            var pk=$(this).closest("div").attr("data-pk");
            var data = {
                'id': pk,
                'table': 'user'
            }

            $("#modalDeleteUserForm")[0].reset();
            $('#modalDeleteUserForm #id').val(JSON.stringify([data]));
			$('#modalDeleteUser').modal({
				backdrop: 'static',
				keyboard: false
			}).modal('show');
            $.ajax({
                type: "POST",
                url: "/api/v3/admin/delete/check",
                data: JSON.stringify(data),
                contentType: "application/json"
            }).done(function(domains) {
                $('#table_modal_delete tbody').empty()
                $.each(domains, function(key, value) {
                    infoDomains(value, $('#table_modal_delete tbody'));
                });  
            });
	});


    $('.btn-active').on('click', function () {
        var closest=$(this).closest("div");
        var id=closest.attr("data-pk");
        var name=closest.attr("data-name");
        var active = users_table.row($(this).closest("tr").prev()).data().active
        new PNotify({
            title: 'Confirmation Needed',
            text: "Are you sure you want to enable/disable: "+name+"?",
            hide: false,
            opacity: 0.9,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            },
            addclass: 'pnotify-center'
        }).get().on('pnotify.confirm', function() {
            $.ajax({
                type: "PUT",
                url: "/api/v3/admin/user/" + id,
                data: JSON.stringify({ id, active }),
                contentType: "application/json",
                success: function(data) {
                    $('form').each(function() { this.reset() });
                    $('.modal').modal('hide');
                    new PNotify({
                        title: "Updated user " + name + " status ",
                        text: "User status has been updated...",
                        hide: true,
                        delay: 4000,
                        icon: 'fa fa-success',
                        opacity: 1,
                        type: "success"
                    });
                },
                error: function(data) {
                    new PNotify({
                        title: "ERROR updating user "+name,
                        text: data.responseJSON.description,
                        type: 'error',
                        hide: true,
                        icon: 'fa fa-warning',
                        delay: 15000,
                        opacity: 1
                    });
                }
            });
        }).on('pnotify.cancel', function() {});
    });

    $('.btn-impersonate').on('click', function () {
        var closest=$(this).closest("div");
        var id=closest.attr("data-pk");
        var name=closest.attr("data-name");
        new PNotify({
            title: 'Confirmation Needed',
            text: "Are you sure you want to impersonate as: "+name+"?",
            hide: false,
            opacity: 0.9,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            },
            addclass: 'pnotify-center'
        }).get().on('pnotify.confirm', function() {
            $.ajax({
                type: "GET",
                url: "/api/v3/admin/jwt/"+id,
            }).done(function (data) {
                localStorage.setItem('token', data.jwt)
                window.location = "/Desktops"
            }).fail(function(data) {
                new PNotify({
                    title: "Impersonate",
                    text: "Not allowed to impersonate as a higher role",
                    hide: true,
                    delay: 4000,
                    icon: 'fa fa-cross',
                    opacity: 1,
                    type: 'error'
                });
            });
        }).on('pnotify.cancel', function() {});
    });
}

function renderUsersDetailPannel ( d ) {
    if(d.id == 'local-default-admin-admin'){
        $('.template-detail-users .btn-delete').hide()
    }else{
        $('.template-detail-users .btn-delete').show()
    }

		$newPanel = $template.clone();
		$newPanel.html(function(i, oldHtml){
            var secondary_groups_names = []
            $.each(d.secondary_groups_data, function(i, group) {
                secondary_groups_names.push(group.name)
            })
			return oldHtml.replace(/d.id/g, d.id).replace(/d.name/g, d.name).replace(/d.username/g, d.username).replace(/d.secondary_groups/g, secondary_groups_names);
        });
		return $newPanel
}

function setModalUser(){
    $.ajax({
        type: "POST",
        url: "/api/v3/admin/userschema",
        data: '',
        contentType: "application/json"
    }).done(function (d) {
        $.each(d, function (key, value) {
            $("." + key).find('option').remove().end();
            for(var i in d[key]){
                    $("."+key).append('<option value=' + value[i].id + '>' + value[i].name + '</option>');
            }
        });
        $('#add-category').trigger("change")
        current_category = ($('#add-category').val())
    });
}

function csv2datatables(csv){
    var exists = false
    $('#bulk-allow-update').iCheck('uncheck').iCheck('update');
    $.ajax({
        type: "POST",
        url: "/api/v3/admin/users/validate/allow_update",
        data: JSON.stringify(parseCSV(csv)),
        contentType: "application/json",
        async: false
    }).done(function (data) {
        $("#csv_correct").show()
        $("#csv_error").hide()
        $("#modalAddBulkUsers #send").attr("disabled", false);
        if ( $.fn.dataTable.isDataTable( '#csv_preview' ) ) {
            $.each( data, function( index, value ){
                if(value.exists){exists=true; return false}
            });
            csv_preview.clear().rows.add(data).draw()
        }else{
            csv_preview=$("#csv_preview").DataTable( {
                data: data,
                rowId: 'username',
                columns: [
                    { "data": "exists", "width": "88px"},
                    { "data": "username", "width": "88px", "className": "no-update"},
                    { "data": "name", "width": "88px"},
                    { "data": "email", "width": "88px"},
                    { "data": "password", "width": "88px"},
                    { "data": "group", "width": "88px", "defaultContent": "", "className": "no-update"},
                    { "data": "category", "width": "88px", "defaultContent": "", "className": "no-update"},
                    { "data": "role", "width": "88px", "defaultContent": ""},
                    ],
                "order": [[0, 'asc']],
                "columnDefs": [
                    {
                    "targets": 0,
                    "render": function ( data, type, full, meta ) {
                        if(full.exists){
                            exists = true
                            return '<i class="fa fa-check" style="color:lightgreen"></i>';
                        }else{
                            return '<i class="fa fa-close" style="color:darkgray"></i>';
                        }
                    }},
                ]
            } );
        }
    }).fail(function(data) {
        $("#csv_correct").hide()
        $("#modalAddBulkUsers #send").attr("disabled", true);
        $("#csv_error #csv_error_html").html(data.responseJSON.description)
        $("#csv_error").show()
        if ( $.fn.dataTable.isDataTable( '#csv_preview' ) ) {
            csv_preview.clear()
        }
    });
}

function parseCSV(csv){
    lines=csv.split(/\r?\n/)
    header=lines[0].split(',')
    users=[]
    $.each(lines, function(n, l){
        if(n!=0 && l.length > 10){
            usr=toObject(header,l.split(','))
            usr['id']=usr['username']
            users.push(usr)
        }
    })
    return users;
}

function toObject(names, values) {
    var result = {};
    for (var i = 0; i < names.length; i++)
         result[names[i]] = values[i];
    return result;
}

