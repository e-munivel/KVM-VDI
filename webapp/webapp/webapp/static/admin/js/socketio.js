/*
 *   IsardVDI - Open Source KVM Virtual Desktops based on KVM Linux and dockers
 *   Copyright (C) 2022 Simó Albert i Beltran
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU Affero General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Affero General Public License for more details.
 *
 *   You should have received a copy of the GNU Affero General Public License
 *   along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

socket = io.connect(`//${location.host}/administrators`, {
    'path': '/api/v3/socket.io/',
    'transports': ['websocket'],
    auth: (cb) => {
        cb({ jwt: getCookie('isardvdi_session') })
    }
})

socket.on('connect', function () {
    connection_done()
})

socket.on('connect_error', (err) => {
    console.log('WS connection error:')
    console.log(err)
    if (err.message === 'timeout') {
        console.log('WS connection timeout')
    } else if (err.message === 'websocket error') {
        console.log('WS connection error')
    } else if (err.message === 'Connection rejected by server') {
        console.log('WS connection not authorized')
        deleteCookie('isardvdi_session')
        window.location = '/isard-admin/logout'
    } else {
        console.log('WS connection error: ' + err)
    }
    connection_lost()
})
