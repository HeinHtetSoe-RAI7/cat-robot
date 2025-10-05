package main

import (
	"log"
	"net/http"
	"os"
	"path/filepath"
)

func main() {
	publicDir := "public"
	port := ":8080"

	fs := http.FileServer(http.Dir(publicDir))
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		path := filepath.Join(publicDir, r.URL.Path)
		info, err := os.Stat(path)
		if err == nil && info.IsDir() {
			index := filepath.Join(path, "index.html")
			if _, err := os.Stat(index); err != nil {
				http.NotFound(w, r)
				return
			}
		}
		fs.ServeHTTP(w, r)
	})

	log.Printf("Serving on http://localhost%s\n", port)
	log.Fatal(http.ListenAndServe(port, nil))
}
