package main

import (
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net"
	"net/http"
	"net/url"
	"os"
	"path"
	"strconv"

	"github.com/sirupsen/logrus"
	"github.com/wwt/guac"
)

var (
	guacdAddr     string
	backendAddr   string
	backendScheme string
)

func init() {
	guacdAddr = os.Getenv("GUACD_ADDR")
	if guacdAddr == "" {
		guacdAddr = "isard-vpn:4822"
	}

	backendAddr = os.Getenv("GUACD_BACKEND_HOST")
	if backendAddr == "" {
		backendAddr = "isard-backend:8080"
		backendScheme = "http"
	} else {
		backendAddr += ":443"
		backendScheme = "https"
	}
}

func isAuthenticated(handler http.Handler) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		u := &url.URL{
			Scheme: backendScheme,
			Host:   backendAddr,
			Path:   path.Join("/api/v2/check-desktop", r.URL.Query().Get("hostname")),
		}

		req, err := http.NewRequest(http.MethodGet, u.String(), nil)
		if err != nil {
			logrus.Fatal("create http request to check for authentication: %v", err)
		}

		session := r.URL.Query().Get("session")
		if session == "" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}

		c := &http.Cookie{
			Name:  "session",
			Value: session,
		}

		req.AddCookie(c)

		rsp, err := http.DefaultClient.Do(req)
		if err != nil {
			logrus.Error("do http request to check for authentication: %v", err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}

		switch rsp.StatusCode {
		case http.StatusOK:
			handler.ServeHTTP(w, r)

		case http.StatusUnauthorized:
			w.WriteHeader(http.StatusUnauthorized)
			return

		default:
			b, err := io.ReadAll(rsp.Body)
			if err != nil {
				logrus.Errorf("read http response: %v", err)
				w.WriteHeader(http.StatusInternalServerError)
				return
			}
			defer rsp.Body.Close()

			w.WriteHeader(rsp.StatusCode)
			w.Write(b)
		}
	})
}

func main() {
	logrus.SetLevel(logrus.DebugLevel)

	servlet := guac.NewServer(DemoDoConnect)
	wsServer := guac.NewWebsocketServer(DemoDoConnect)

	sessions := guac.NewMemorySessionStore()
	wsServer.OnConnect = sessions.Add
	wsServer.OnDisconnect = sessions.Delete

	mux := http.NewServeMux()
	mux.HandleFunc("/tunnel", isAuthenticated(servlet))
	mux.HandleFunc("/tunnel/", isAuthenticated(servlet))
	mux.HandleFunc("/websocket-tunnel", isAuthenticated(wsServer))
	mux.HandleFunc("/sessions/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		sessions.RLock()
		defer sessions.RUnlock()

		type ConnIds struct {
			Uuid string `json:"uuid"`
			Num  int    `json:"num"`
		}

		connIds := make([]*ConnIds, len(sessions.ConnIds))

		i := 0
		for id, num := range sessions.ConnIds {
			connIds[i] = &ConnIds{
				Uuid: id,
				Num:  num,
			}
		}

		if err := json.NewEncoder(w).Encode(connIds); err != nil {
			logrus.Error(err)
		}
	})

	logrus.Println("Serving on http://127.0.0.1:4567")

	s := &http.Server{
		Addr:           "0.0.0.0:4567",
		Handler:        mux,
		ReadTimeout:    guac.SocketTimeout,
		WriteTimeout:   guac.SocketTimeout,
		MaxHeaderBytes: 1 << 20,
	}
	err := s.ListenAndServe()
	if err != nil {
		fmt.Println(err)
	}
}

// DemoDoConnect creates the tunnel to the remote machine (via guacd)
func DemoDoConnect(request *http.Request) (guac.Tunnel, error) {
	config := guac.NewGuacamoleConfiguration()

	var query url.Values
	if request.URL.RawQuery == "connect" {
		// http tunnel uses the body to pass parameters
		data, err := ioutil.ReadAll(request.Body)
		if err != nil {
			logrus.Errorf("Failed to read body ", err)
			return nil, err
		}
		_ = request.Body.Close()
		queryString := string(data)
		query, err = url.ParseQuery(queryString)
		if err != nil {
			logrus.Errorf("Failed to parse body query ", err)
			return nil, err
		}
		logrus.Debugln("body:", queryString, query)
	} else {
		query = request.URL.Query()
	}

	config.Protocol = query.Get("scheme")
	config.Parameters = map[string]string{}
	for k, v := range query {
		config.Parameters[k] = v[0]
	}

	var err error
	if query.Get("width") != "" {
		config.OptimalScreenHeight, err = strconv.Atoi(query.Get("width"))
		if err != nil || config.OptimalScreenHeight == 0 {
			logrus.Error("Invalid height")
			config.OptimalScreenHeight = 600
		}
	}
	if query.Get("height") != "" {
		config.OptimalScreenWidth, err = strconv.Atoi(query.Get("height"))
		if err != nil || config.OptimalScreenWidth == 0 {
			logrus.Error("Invalid width")
			config.OptimalScreenWidth = 800
		}
	}
	config.AudioMimetypes = []string{"audio/L16", "rate=44100", "channels=2"}

	logrus.Debug("Connecting to guacd")
	addr, err := net.ResolveTCPAddr("tcp", guacdAddr)
	if err != nil {
		logrus.Errorf("resolve guacd address: %v", err)
		return nil, err
	}

	conn, err := net.DialTCP("tcp", nil, addr)
	if err != nil {
		logrus.Errorf("error while connecting to guacd", err)
		return nil, err
	}

	stream := guac.NewStream(conn, guac.SocketTimeout)

	logrus.Debug("Connected to guacd")
	if request.URL.Query().Get("uuid") != "" {
		config.ConnectionID = request.URL.Query().Get("uuid")
	}
	logrus.Debugf("Starting handshake with %#v", config)
	err = stream.Handshake(config)
	if err != nil {
		return nil, err
	}
	logrus.Debug("Socket configured")
	return guac.NewSimpleTunnel(stream), nil
}
