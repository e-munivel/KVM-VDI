/*
* Copyright 2017 the Isard-vdi project authors:
*      Josep Maria Viñolas Auquer
*      Alberto Larraz Dalmases
* License: AGPLv3
*/

var $template='';
var table='';
$(document).ready(function() {
    $('.admin-status').hide()
    $template = $(".template-detail");
    table = $('#templates').DataTable({
            "ajax": {
                "url": "/isard-admin/template/get/",
                "dataSrc": ""
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
                "defaultContent": '<button id="btn-detail" class="btn btn-xs btn-info" type="button"  data-placement="top" ><i class="fa fa-plus"></i></button>'
                },
                { "data": "icon", "width": "10px" },
                { "data": "name"},
                { "data": "status"},
                {
                    "data": 'enabled',
                    "className": 'text-center',
                    "data": null,
                    "orderable": false,
                    "defaultContent": '<input type="checkbox" class="form-check-input" checked></input>'
                },
                { "data": null, 'defaultContent': ''},
                { "data": "description", "visible": false},
                
                ],
             "order": [[2, 'asc']],
             "columnDefs": [ {
                            "targets": 1,
                            "render": function ( data, type, full, meta ) {
                                url = location.protocol+'//' + document.domain + ':' + location.port + full.image.url
                                return "<img src='"+url+"' width='50px'>"
                            }},
                            {
                            "targets": 2,
                            "render": function ( data, type, full, meta ) {
                              return renderName(full);
                            }},
                            {
                            "targets": 3,
                            "render": function ( data, type, full, meta ) {
                              return renderStatus(full);
                            }},
                            {
                            "targets": 4,
                            "render": function ( data, type, full, meta ) {
                                if( full.enabled ){
                                    return '<input id="chk-enabled" type="checkbox" class="form-check-input" checked></input>'
                                }else{
                                    return '<input id="chk-enabled" type="checkbox" class="form-check-input"></input>'
                                }
                            }},
                            {
                                "targets": 5,
                                "render": function ( data, type, full, meta ) {
                                    if(full.status == 'Stopped' || full.status == 'Stopped'){
                                        return '<button id="btn-alloweds" class="btn btn-xs" type="button"  data-placement="top" ><i class="fa fa-users" style="color:darkblue"></i></button>'
                                    } 
                                    return full.status; 
                                }},
                            ]
        } );
    
    $('#templates').find('tbody').on('click', 'td.details-control', function () {
        var tr = $(this).closest('tr');
        var row = table.row( tr );
        if ( row.child.isShown() ) {
            // This row is already open - close it
            row.child.hide();
            row.child.remove();
            tr.removeClass('shown');
        }
        else {
            // Close other rows
            if ( table.row( '.shown' ).length ) {
                $('.details-control', table.row( '.shown' ).node()).click();
            }
            // Open this row
            row.child( formatPanel(row.data()) ).show();
            tr.addClass('shown');
            setHardwareDomainDefaults_viewer('#hardware-'+row.data().id,row.data());
	    //~ setDomainGenealogy(row.data().id)
            setAlloweds_viewer('#alloweds-'+row.data().id,row.data().id);
            actionsTmplDetail();
            
        }
    });

    $('#templates').find(' tbody').on( 'click', 'input', function () {
        var pk=table.row( $(this).parents('tr') ).id();
        switch($(this).attr('id')){
            case 'chk-enabled':
                if ($(this).is(":checked")){
                    enabled=true
                }else{
                    enabled=false
                }
                api.ajax('/isard-admin/template',
                        'PUT',
                        {'id':pk,
                        'enabled':enabled})
                .fail(function(jqXHR) {
                    new PNotify({
                        title: "Template enable/disable",
                            text: "Could not update!",
                            hide: true,
                            delay: 3000,
                            icon: 'fa fa-alert-sign',
                            opacity: 1,
                            type: 'error'
                        });
                        table.ajax.reload()
                }); 
            break;
        }
    })

    $('#templates').find(' tbody').on( 'click', 'button', function () {
        var data = table.row( $(this).parents('tr') ).data();

        switch($(this).attr('id')){
            //~ case 'btn-detail':
                //~ var tr = $(this).closest('tr');
                //~ var row = table.row( tr );
                //~ if ( row.child.isShown() ) {
                    //~ // This row is already open - close it
                    //~ row.child.hide();
                    //~ row.child.remove();
                    //~ tr.removeClass('shown');
                //~ }
                //~ else {
                    //~ // Open this row
                    //~ row.child( formatPanel(row.data()) ).show();
                    //~ tr.addClass('shown');
                    //~ setHardwareDomainDefaults_viewer('#hardware-'+row.data().id,row.data().id);
                    //~ setHardwareGraph();
                    //~ setAlloweds_viewer('#alloweds-'+row.data().id,row.data().id);
                    //~ actionsTmplDetail();
                    
                //~ }
                //~ break;
             case 'btn-alloweds':
                    modalAllowedsFormShow('domains',data)
             break;                
        };
    });   

   
    //~ Delete confirm modal
    $('#confirm-modal > .modal-dialog > .modal-content > .modal-footer > .btn-primary').click(function() {
        //~ console.log('id:'+$('#confirm-modal').data('id')+' - action: delete');
        // Needs some work
        });
        
    $('#confirm-modal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget);
      var id = button.data('id'); // Extract data-* attributes
      var name = button.data('name');
      var modal = $(this);
      modal.data('id',id);
      modal.find('.modal-title').text('Do you really want to remove "' + name + '" desktop?');
      modal.find('.modal-body').text('The desktop will be permanently deleted (unrecoverable)')
    });

    // SocketIO
        socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port+'/isard-admin/sio_users', {
        'path': '/isard-admin/socket.io/',
        'transports': ['websocket']
    });

    socket.on('connect', function() {
        connection_done();
        console.log('Listening user namespace');
    });

    socket.on('connect_error', function(data) {
      connection_lost();
    });
    
    socket.on('user_quota', function(data) {
        console.log('Quota update')
        var data = JSON.parse(data);
        drawUserQuota(data);
    });

    socket.on('template_data', function(data){
        //~ console.log('update')
        var data = JSON.parse(data);
        dtUpdateInsert(table,data,false);
        //~ setDesktopDetailButtonsStatus(data.id, data.status);

        
        //~ var data = JSON.parse(data);
        //~ var row = table.row('#'+data.id); 
        //~ table.row(row).data(data);
        //~ setDesktopDetailButtonsStatus(data.id, data.status);
    });

    socket.on('template_add', function(data){
        //~ console.log('add')
        var data = JSON.parse(data);
        if($("#" + data.id).length == 0) {
          //it doesn't exist
          table.row.add(data).draw();
        }else{
          //if already exists do an update (ie. connection lost and reconnect)
          var row = table.row('#'+data.id); 
          table.row(row).data(data);            
        }
    });
    
    socket.on('template_delete', function(data){
        //~ console.log('delete')
        var data = JSON.parse(data);
        var row = table.row('#'+data.id).remove().draw();
        new PNotify({
                title: "Desktop deleted",
                text: "Desktop "+data.name+" has been deleted",
                hide: true,
                delay: 4000,
                icon: 'fa fa-success',
                opacity: 1,
                type: 'info'
        });
    });

//~ // SERVER SENT EVENTS Stream
    //~ if (!!window.EventSource) {
      //~ var desktops_source = new EventSource('/stream/isard-admin/desktops');
      //~ console.log('on event');
    //~ } else {
      //~ // Result to xhr polling :(
    //~ }

    //~ window.onbeforeunload = function(){
      //~ desktops_source.close();
    //~ };

    //~ desktops_source.addEventListener('New', function(e) {
      //~ var data = JSON.parse(e.data);
        //~ if($("#" + data.id).length == 0) {
          //~ //it doesn't exist
          //~ table.row.add( formatTmplDetails(data)).draw();
        //~ }else{
          //~ //if already exists do an update (ie. connection lost and reconnect)
            //~ var row = table.row('#'+data.id); 
            //~ table.row(row).data(formatTmplDetails(data));           
        //~ }
      
        //~ if(data.status=='Stopped'){
            //~ // Should disable details buttons
        //~ }else{
            //~ // And enable it again
        //~ }
    //~ }, false);

    //~ desktops_source.addEventListener('Status', function(e) {
      //~ var data = JSON.parse(e.data);
      //~ var row = table.row('#'+data.id); 
      //~ table.row(row).data(formatTmplDetails(data));
    //~ }, false);

    //~ desktops_source.addEventListener('Deleted', function(e) {
      //~ var data = JSON.parse(e.data);
      //~ // var row =
        //~ table.row('#'+data.id).remove().draw();
    //~ }, false);


});   // document ready

function formatTmplDetails(data){
        var row=$('*[data-pk="'+data.id+'"]');
        if(data.status=='Stopped'){
            row.find('.btn-delete').prop('disabled', false);
        }else{
            row.find('.btn-delete').prop('disabled', true);
        }
        return data;
}

function formatPanel ( d ) {
        $newPanel = $template.clone();
        $newPanel.html(function(i, oldHtml){
            return oldHtml.replace(/d.id/g, d.id).replace(/d.name/g, d.name).replace(/d.kind/g, d.kind);
        });
        if(d.status=='Stopped'){
            $newPanel.find('.btn-actions').prop('disabled', false);
        }else{
            $newPanel.find('.btn-actions').prop('disabled', true);
        }
        return $newPanel
}
    
function actionsTmplDetail(){
        $('.btn-edit').on('click', function () {
            // Not implemented
        });

        $('.btn-delete').on('click', function () {
                var pk=$(this).closest("div").attr("data-pk");
                var name=$(this).closest("div").attr("data-name");
                new PNotify({
                        title: 'Confirmation Needed',
                            text: "Are you sure you want to delete template: "+name+"?",
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
                            api.ajax('/isard-admin/domains/removable','POST',{'id':pk}).done(function(data) {
                                //console.log('data received:'+data);
                            }); 
			    			    
                            //~ api.ajax('/isard-admin/domains/update','POST',{'pk':pk,'name':'status','value':'Deleting'}).done(function(data) {
                                //~ console.log('data received:'+data);
                            //~ });  
                        }).on('pnotify.cancel', function() {
                }); 
            });
    }

    function icon(name){
       if(name=='windows' || name=='linux'){
           return "<span ><i class='fa fa-"+name+" fa-2x'></i></span>";
        }else{
            return "<span class='fl-"+name+" fa-2x'></span>";
        }       
    }

    function renderName(data){
        return '<div class="block_content" > \
                <h4 class="title" style="margin-bottom: 0.1rem; margin-top: 0px;"> \
                <a>'+data.name+'</a> \
                </h4> \
                <p class="excerpt" >'+data.description+'</p> \
                </div>'
    }
        
    function renderStatus(data){
        return data.status
    }   
    
    function renderPending(data){
        status=data.status;
        if(status=='Stopped'){
            return 'None';
        }
        return '<div class="Change"> <i class="fa fa-spinner fa-pulse fa-2x fa-fw"></i><span class="sr-only">Working...</span></i> </div>';
    }   
