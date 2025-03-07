    // SocketIO
        socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port+'/isard-admin/sio_users', {
        'path': '/isard-admin/socket.io/',
        'transports': ['websocket']
    });
     
    socket.on('connect', function() {
        connection_done();
        console.log('Listening users namespace for quota');
    });

    socket.on('connect_error', function(data) {
      connection_lost();
    });
    
    socket.on('user_quota', function(data) {
        console.log('Quota update')
        var data = JSON.parse(data);
        drawUserQuota(data);
    });
