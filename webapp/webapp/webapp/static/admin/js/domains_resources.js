/*
* Copyright 2017 the Isard-vdi project authors:
*      Josep Maria Viñolas Auquer
*      Alberto Larraz Dalmases
* License: AGPLv3
*/


$(document).ready(function() {
    $('.admin-status').show()

    remotevpn_table=$('#table-remotevpn').DataTable({
        "ajax": {
            "url": "/admin/table/remotevpn",
            "contentType": "application/json",
            "type": 'POST',
            "data": function(d){return JSON.stringify({'order_by':'name'})}
        },
        "sAjaxDataProp": "",
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
            "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
            },
            { "data": "name"},
            { "data": "description"},
            { "data": null},
            { "data": null},
            { "data": "vpn-wireguard-connected" , "width": "10px", "defaultContent": 'NaN' },
            {
            "className":      'actions-control',
            "orderable":      false,
            "data":           null,
            "width":          "290px",
            "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button> \
                                <button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button> \
                                <button id="btn-download" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-download" style="color:darkgreen"></i></button>'
                               //<button id="btn-edit" class="btn btn-xs btn-edit-interface" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
            },
            ],
         "order": [[1, 'asc']],
         "columnDefs": [ {
            "targets": 3,
            "render": function ( data, type, full, meta ) {
                if('vpn' in data){
                    return data['vpn']['wireguard']['Address']
                }else{
                    return '-'
                }
            }},
            {
            "targets": 4,
            "render": function ( data, type, full, meta ) {
                if('vpn' in data){
                    return data['vpn']['wireguard']['extra_client_nets']
                }else{
                    return '-'
                }
            }},
            {
                "targets": 5,
                "render": function ( data, type, full, meta ) {
                    if('vpn' in full && full['vpn']['wireguard']['connected']){
                        return '<i class="fa fa-circle" aria-hidden="true"  style="color:green"></i>'
                    }else{
                        return '<i class="fa fa-circle" aria-hidden="true"  style="color:darkgray"></i>'
                    }
                }},
            ]
    } );

    $('#table-remotevpn').find(' tbody').on( 'click', 'button', function () {
        var data = remotevpn_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('remotevpn',data)
            break;
            case 'btn-edit':
                $("#modalRemotevpnForm")[0].reset();
                $('#modalRemotevpn').modal({
                    backdrop: 'static',
                    keyboard: false
                }).modal('show');
                $('#modalRemotevpn #modalRemotevpnForm').parsley();
                api.ajax('/isard-admin/admin/load/remotevpn/post','POST',{'id':data.id}).done(function(remotevpn) {
                    $('#modalRemotevpnForm #name').val(remotevpn.name).attr("disabled",true);
                    $('#modalRemotevpnForm #id').val(remotevpn.id);
                    $('#modalRemotevpnForm #description').val(remotevpn.description);
                    $.each(remotevpn,function(key,value){
                        $('#modalRemotevpnForm #'+key).val(value)
                    });             
                });
            break;
            case 'btn-delete':
                new PNotify({
                    title: 'Confirmation Needed',
                        text: "Are you sure you want to delete client VPN: "+data['name']+"?",
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
                        data['table']='remotevpn'
                        socket.emit('resources_delete',data)
                    }).on('pnotify.cancel', function() {
            });	
            break;
            case 'btn-download':
                socket.emit('vpn',{'vpn':'remotevpn','kind':'config','id':data['id'],'os':getOS()});
            break;
        }
    });

    $('.add-new-remotevpn').on( 'click', function () {
            $('#modalRemotevpnForm #name').attr("disabled",false);
            $("#modalRemotevpnForm")[0].reset();
            $('#modalRemotevpn').modal({
                backdrop: 'static',
                keyboard: false
            }).modal('show');
            $('#modalRemotevpn #modalRemotevpnForm').parsley();
    });

    $("#modalRemotevpn #send").on('click', function(e){
        var form = $('#modalRemotevpnForm');
        data = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){  
            if(data['id']==""){
                //Insert
                data['id']=false;
                data['allowed']={'roles':false,'categories':false,'groups':false,'users':false}
            }else{
                //Update
                    data['name']=$('#modalRemotevpnForm #name').val();
                }
            data['table']='remotevpn'
            socket.emit('resources_insert_update',data)
        }
        });

        // QOS NET
        qosnet_table=$('#table-qos-net').DataTable({
            "ajax": {
				"url": "/admin/table/qos_net",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
            },
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
                },
                { "data": "name"},
                { "data": "description"},
                {
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button> \
                                    <button id="btn-edit" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
                                //~ <button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button>'
                    
                },                
                ],
            "order": [[1, 'asc']]
    } );

    $('#table-qos-net').find(' tbody').on( 'click', 'button', function () {
        var data = qosnet_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('qos_net',data)
            break;
            case 'btn-edit':
                $("#modalQosNetForm")[0].reset();
                $('#modalQosNet').modal({
                    backdrop: 'static',
                    keyboard: false
                }).modal('show');
                $('#modalQosNet #modalQosNetForm').parsley();
                api.ajax('/isard-admin/admin/load/qos_net/post','POST',{'id':data.id}).done(function(qos) {
                    (qos)
                    $('#modalQosNetForm #name').val(qos.name).attr("disabled",true);
                    $('#modalQosNetForm #id').val(qos.id);
                    $('#modalQosNetForm #description').val(qos.description);
                    qos=removeQosAd(qos)
                    $.each(qos,function(key,value){
                        $('#modalQosNetForm #qos-'+key).val(value)
                    });             
                });
            break;
            case 'btn-delete':
                // update_keyvalue on admin_api 
                // update qos_id from all interfaces to false
                new PNotify({
                    title: 'Confirmation Needed',
                        text: "Are you sure you want to delete: "+data.name+"? It will be removed from all depending interfaces.",
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
                        socket.emit('user_toggle',{'pk':pk,'name':name})
                    }).on('pnotify.cancel', function() {
                });	                
        }
    });

    $('.add-new-qos-net').on( 'click', function () {
            $('#modalQosNetForm #name').attr("disabled",false);
            $("#modalQosNetForm")[0].reset();
            $('#modalQosNet').modal({
                backdrop: 'static',
                keyboard: false
            }).modal('show');
            $('#modalQosNet #modalQosNetForm').parsley();

    });

    $("#modalQosNet #send").on('click', function(e){
        console.log('send net')
        var form = $('#modalQosNetForm');
        data = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){   
            
            data=QosNetParse(data)
            if(data['id']==""){
                //Insert
                data['id']=false;
                data['allowed']={'roles':false,'categories':false,'groups':false,'users':false}
            }else{
                //Update
                    data['name']=$('#modalQosNetForm #name').val();
                }
            data['table']='qos_net'                   
            socket.emit('resources_insert_update',data)
        }
    });
    
        
    // QOS DISK
        qosdisk_table=$('#table-qos-disk').DataTable({
            "ajax": {
				"url": "/admin/table/qos_disk",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
            },
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
                },
                { "data": "name"},
                { "data": "description"},
                {
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button> \
                                    <button id="btn-edit" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
                                //~ <button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button>'
                    
                },                
                ],
            "order": [[1, 'asc']]
    } );

    $('#table-qos-disk').find(' tbody').on( 'click', 'button', function () {
        var data = qosdisk_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('qos_disk',data)
            break;
            case 'btn-edit':
                $("#modalQosDiskForm")[0].reset();
                $('#modalQosDisk').modal({
                    backdrop: 'static',
                    keyboard: false
                }).modal('show');
                $('#modalQosDisk #modalQosDiskForm').parsley();
                api.ajax('/isard-admin/admin/load/qos_disk/post','POST',{'id':data.id}).done(function(qos) {
                    $('#modalQosDiskForm #name').val(qos.name).attr("disabled",true);
                    $('#modalQosDiskForm #id').val(qos.id);
                    $('#modalQosDiskForm #description').val(qos.description);
                    qos=removeQosAd(qos)
                    $.each(qos,function(key,value){
                        $('#modalQosDiskForm #'+key).val(value)
                    });             
                });
            break;
                
        }
    });

    $('.add-new-qos-disk').on( 'click', function () {
            $('#modalQosDiskForm #name').attr("disabled",false);
            $("#modalQosDiskForm")[0].reset();
            $('#modalQosDisk').modal({
                backdrop: 'static',
                keyboard: false
            }).modal('show');
            $('#modalQosDisk #modalQosDiskForm').parsley();

    });

    $("#modalQosDisk #send").on('click', function(e){
        var form = $('#modalQosDiskForm');
        data = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){   
            data['allowed']={'roles':false,'categories':false,'groups':false,'users':false}
            data=QosDiskParse(data)
            if(data['id']==""){
                //Insert
                data['id']=false;
                data['allowed']={'roles':false,'categories':false,'groups':false,'users':false}
            }else{
                //Update
                    data['name']=$('#modalQosDiskForm #name').val();
                }
            data['table']='qos_disk'                   
            socket.emit('resources_insert_update',data)
        }
            
    });


    // INTERFACES

    $('#kind').on('change', function () {
        if($('#kind').val() == 'bridge'){
            $('#ifname_label').html('Input interface name')
        }
        if($('#kind').val() == 'network'){
            $('#ifname_label').html('Input network name')
        }
        if($('#kind').val() == 'ovs'){
            $('#ifname_label').html('Input vlan ID number')
        }
        if($('#kind').val() == 'personal'){
            $('#ifname_label').html('Input vlan range (2000-3000)')
        }
    });
    int_table=$('#table-interfaces').DataTable({
			"ajax": {
				"url": "/admin/table/interfaces",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
			},
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
				},
				{ "data": "name"},
				{ "data": "description"},
                { "data": "net"},
				{
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "width":          "91px",
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button> \
                                    <button id="btn-edit" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button> \
                                    <button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button>'
                },
                ],
            "order": [[1, 'asc']],
    } );

    $('#table-interfaces').find(' tbody').on( 'click', 'button', function () {
        var data = int_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('interfaces',data)
            break;
            case 'btn-edit':
                $("#modalInterfacesForm")[0].reset();
                $('#modalInterfaces').modal({
                    backdrop: 'static',
                    keyboard: false
                }).modal('show');
                $('#modalInterfaces #modalInterfacesForm').parsley();
                api.ajax('/isard-admin/admin/load/interfaces/post','POST',{'id':data.id}).done(function(interface) {
                    if('qos_id' in data){
                        if(data['qos_id'] == false){
                            qos_id='unlimited'
                        }else{
                            qos_id=data['qos_id']
                        }
                    }else{qos_id='unlimited'}
                    populateDropdown('qos_net','#qos_id',qos_id, false)
                    $('#modalInterfacesForm #name').val(interface.name).attr("disabled",true);
                    $('#modalInterfacesForm #id').val(interface.id);
                    $('#modalInterfacesForm #description').val(interface.description);
                    $.each(interface,function(key,value){
                        $('#modalInterfacesForm #'+key).val(value)
                    });
                });
                break;
                case 'btn-delete':
                new PNotify({
                    title: 'Confirmation Needed',
                        text: "Are you sure you want to delete: "+data.name+"? WARNING: ALL STARTED DESKTOPS WITH THIS INTERFACE WILL BE STOPPED before the interface will be removed from all depending desktops & templates.",
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
                        socket.emit('interface_delete',{'pk':data.id,'name':data.name})
                    }).on('pnotify.cancel', function() {
                });
                break;
        }
    });

    $('.add-new-interface').on( 'click', function () {
            $('#modalInterfacesForm #name').attr("disabled",false);
            $("#modalInterfacesForm")[0].reset();
            $('#modalInterfaces').modal({
                backdrop: 'static',
                keyboard: false
            }).modal('show');
            populateDropdown('qos_net','#qos_id','unlimited',false)
            $('#modalInterfaces #modalInterfacesForm').parsley();

            window.Parsley.addValidator('cidr', {
                validateString: function(value, id) {
                          var ip = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/([0-9]|[1-2][0-9]|3[0-2]))$";
                          return value.match(ip);
                },
                messages: {
                  en: 'This string is not CIDR format'
                }
              });
    });

    $("#modalInterfaces #send").on('click', function(e){
        var form = $('#modalInterfacesForm');
        data = form.serializeObject()
        form.parsley().validate();
        if (form.parsley().isValid()){   
            if(data['id']==""){
                //Insert
                data['id']=false;
                data['allowed']={'roles':false,'categories':false,'groups':false,'users':false}
            }else{
                //Update
                    data['name']=$('#modalInterfacesForm #name').val();
            }
            data['net']=data['ifname']
            data['table']='interfaces'             
            socket.emit('resources_insert_update',data)
        }
            
    });










    // GRAPHICS
    graphics_table=$('#graphics').DataTable({
			"ajax": {
				"url": "/admin/table/graphics",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
			},
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
				},
				{ "data": "name"},
				{ "data": "description"},
				{
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button>'
                                    //~ '<button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button> \
                                   //~ <button id="btn-edit" class="btn btn-xs btn-edit-interface" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
				},                
                ],
			 "order": [[1, 'asc']]
    } );

    $('#graphics').find(' tbody').on( 'click', 'button', function () {
        var data = graphics_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('graphics',data)
            break;
                
        }
    });
    
	$('.add-new-graphics').on( 'click', function () {
            $("#modalGraphics #modalAddGraphics")[0].reset();
			$('#modalGraphics').modal({
				backdrop: 'static',
				keyboard: false
			}).modal('show');
            $('#modalGraphics #modalAddGraphics').parsley();
            setAlloweds_add('#alloweds-graphics-add');
	});

    $("#modalGraphics #send").on('click', function(e){
            var form = $('#modalAddGraphics');
            form.parsley().validate();
            data=$('#modalAddGraphics').serializeObject();
            data=replaceAlloweds_arrays('#modalAddGraphics #alloweds-graphics-add', data)
            data['id']=false
            data['table']='graphics'
            socket.emit('resources_insert_update', data)
        });

    // VIDEOS
    videos_table=$('#videos').DataTable({
			"ajax": {
				"url": "/admin/table/videos",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
			},
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
				},
				{ "data": "name"},
				{ "data": "description"},
				{
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button>'
                                    //~ '<button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button> \
                                   //~ <button id="btn-edit" class="btn btn-xs btn-edit-interface" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
				},                
                ],
			 "order": [[1, 'asc']]
    } );

    $('#videos').find(' tbody').on( 'click', 'button', function () {
        var data = videos_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('videos',data)
            break;
            case 'btn-bookable': 
                if( data['bookable'] ){    
                    new PNotify({
                        title: 'Confirmation Needed',
                            text: "Are you sure you want to remove "+data['name']+" as a bookable resource? All bookings done will be removed!",
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
                            data['table']='videos'
                            socket.emit('bookable_add',data)
                        }).on('pnotify.cancel', function() {
                    });
                }else{
                    new PNotify({
                        title: 'Confirmation Needed',
                            text: "Are you sure you want to add "+data['name']+" as a bookable resource?",
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
                            data['table']='videos'
                            socket.emit('bookable_delete',data)
                        }).on('pnotify.cancel', function() {
                    });
                }
            break;
        }
    });
    
	$('.add-new-videos').on( 'click', function () {
            $("#modalVideos #modalAddVideos")[0].reset();
			$('#modalVideos').modal({
				backdrop: 'static',
				keyboard: false
			}).modal('show');
            $('#modalVideos #modalAddVideos').parsley();
            setAlloweds_add('#alloweds-videos-add');
            setRangeSliders();
	});

    $("#modalVideos #send").on('click', function(e){
            var form = $('#modalAddVideos');
            form.parsley().validate();
            data=$('#modalAddVideos').serializeObject();
            data=replaceAlloweds_arrays('#modalAddVideos #alloweds-videos-add', data)
            data['id']=false
            data['table']='videos'
            socket.emit('resources_insert_update', data)
        }); 

    function setRangeSliders(id){
        				$("#videos-heads").ionRangeSlider({
						  type: "single",
						  min: 1,
						  max: 4,
                          step:1,
						  grid: true,
						  disable: false
						  }).data("ionRangeSlider").update();
        				$("#videos-ram").ionRangeSlider({
						  type: "single",
						  min: 8000,
						  max: 128000,
                          step:8000,
						  grid: true,
						  disable: false
						  }).data("ionRangeSlider").update();
        				$("#videos-vram").ionRangeSlider({
						  type: "single",
						  min: 8000,
						  max: 128000,
                          step:8000,
						  grid: true,
						  disable: false
						  }).data("ionRangeSlider").update();                          
    }



    // BOOTS
    boots_table=$('#boots').DataTable({
			"ajax": {
				"url": "/admin/table/boots",
                "contentType": "application/json",
                "type": 'POST',
                "data": function(d){return JSON.stringify({'order_by':'name'})}
			},
            "sAjaxDataProp": "",
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
                "defaultContent": '' //'<button class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
				},
				{ "data": "name"},
				{ "data": "description"},
				{
                "className":      'actions-control',
                "orderable":      false,
                "data":           null,
                "defaultContent": '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button>'
                                    //~ '<button id="btn-delete" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-times" style="color:darkred"></i></button> \
                                   //~ <button id="btn-edit" class="btn btn-xs btn-edit-interface" type="button"  data-placement="top" ><i class="fa fa-pencil" style="color:darkblue"></i></button>'
				},                
                ],
			 "order": [[1, 'asc']]
    } );

    $('#boots').find(' tbody').on( 'click', 'button', function () {
        var data = boots_table.row( $(this).parents('tr') ).data();
        switch($(this).attr('id')){
            case 'btn-alloweds':        
                modalAllowedsFormShow('boots',data)
            break;
                
        }
    });    

    // SocketIO
        socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port+'/isard-admin/sio_admins', {
        'path': '/isard-admin/socket.io/',
        'transports': ['websocket']
    });
     
    socket.on('connect', function() {
        connection_done();
        socket.emit('join_rooms',['resources'])
        console.log('Listening resources namespace');
    });

    socket.on('connect_error', function(data) {
      connection_lost();
    });

    socket.on('user_quota', function(data) {
        console.log('Quota update')
        var data = JSON.parse(data);
        drawUserQuota(data);
    });
    
    socket.on('data', function(data){
        var dict = JSON.parse(data);
        switch(dict['table']){
            case 'graphics':
                dtUpdateInsert(graphics_table,dict['data'],false);
                break;
            case 'videos':
                dtUpdateInsert(videos_table,dict['data'],false);
                break;
            case 'interfaces':
                dtUpdateInsert(int_table,dict['data'],false);
                break;
            case 'boots':
                dtUpdateInsert(boots_table,dict['data'],false);
                break;
            case 'qos_net':
                dtUpdateInsert(qosnet_table,dict['data'],false);
                break;
            case 'qos_disk':
                dtUpdateInsert(qosdisk_table,dict['data'],false);
                break;
            case 'remotevpn':
                dtUpdateInsert(remotevpn_table,dict['data'],false);
                break;
        }  

    });

    socket.on('vpn', function (data) {
        var data = JSON.parse(data);
        if(data['kind']=='url'){
            window.open(data['url'], '_blank');            
        }
        if(data['kind']=='file'){
            var vpnFile = new Blob([data['content']], {type: data['mime']});
            var a = document.createElement('a');
                a.download = data['name']+'.'+data['ext'];
                a.href = window.URL.createObjectURL(vpnFile);
            var ev = document.createEvent("MouseEvents");
                ev.initMouseEvent("click", true, false, self, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                a.dispatchEvent(ev);              
        }
    });

    socket.on('add_form_result', function (data) {
        var data = JSON.parse(data);
        if(data.result){
            $('form').each(function() { this.reset() });
            $('.modal').modal('hide');
            
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
        //users_table.ajax.reload()
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
        //users_table.ajax.reload()
    });  

    socket.on('delete', function(data){
        //~ console.log('delete')
        var dict = JSON.parse(data);
        data=dict['data']        
        //~ var row = table.row('#'+data.id).remove().draw();
        switch(dict['table']){
            case 'graphics':
                var row = graphics_table.row('#'+data.id).remove().draw();
                break;
            case 'videos':
                var row = videos_table.row('#'+data.id).remove().draw();
                break;                
            case 'interfaces':
                var row = int_table.row('#'+data.id).remove().draw();
                break;                    
            case 'boots':
                var row = boots_table.row('#'+data.id).remove().draw();
                break;
            case 'qos_net':
                var row = qosnet_table.row('#'+data.id).remove().draw();
                break;
            case 'qos_disk':
                var row = qosdisk_table.row('#'+data.id).remove().draw();
                break;
            case 'remotevpn':
                var row = remotevpn_table.row('#'+data.id).remove().draw();
                break;
        }        
        new PNotify({
                title: "Resource deleted",
                text: "Resource "+data.name+" has been deleted",
                hide: true,
                delay: 4000,
                icon: 'fa fa-success',
                opacity: 1,
                type: 'success'
        });
    });    

        
});

function removeQosAd(data){
    $.each(data,function(key,value){  
        if(key.includes('@')){
            data[key.split('@')[0]+key.split('@')[1]]=value
            delete data[key]
        }
    });
    return data;
}

function QosDiskParse(data){
    data['iotune']={}
    $.each(data,function(key,value){             
        if(key.startsWith('iotune-')){
            data['iotune']['@'+key.split('-')[1]] = parseInt(value)  || 0
            delete data[key];
            //console.log('Key: '+key+'   - Parsed key: '+'@'+key.split('-')[1])
        }  
    });
    return data;
}

function QosNetParse(data){
    data['bandwidth']={'inbound':{},'outbound':{}}
    $.each(data,function(key,value){
        if(key.startsWith('qos-bandwidth-inbound')){
            data['bandwidth']['inbound']['@'+key.split('-')[3]] = parseInt(value)  || 0
            delete data[key];
        }   
        if(key.startsWith('qos-bandwidth-outbound')){
            data['bandwidth']['outbound']['@'+key.split('-')[3]] = parseInt(value)  || 0
            delete data[key];
        }                  
    });
    return data;
}


function populateDropdown(table, dropdown_id, selected_id, custom){
    $(dropdown_id).find('option').remove().end();
    pluck=['id','name','description']
    api.ajax('/isard-admin/admin/load/'+table+'/post','POST',{'pluck':pluck}).done(function(data) {
        if(!(custom == false)){
            $(dropdown_id).append('<option value=' + custom.id + '>' + custom.name + '</option>');
        }
        data.forEach(function(item){
            $(dropdown_id).append('<option title="'+item.description+'" value=' + item.id + '>' + item.name + '</option>');           
        });
        if(selected_id != false){
            $(dropdown_id+' option[value="'+selected_id+'"]').prop("selected",true);
        }
    });
}