import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog
import re
import os

class MusicDownloader:
    def __init__(self, master):
        self.master = master
        master.title("Music Downloader")

        # Search song section
        tk.Label(master, text="Song keyword:").grid(row=0, column=0, padx=10, pady=10)
        self.keyword_entry = tk.Entry(master, width=30)
        self.keyword_entry.grid(row=0, column=1, padx=10, pady=10)
        self.search_button = tk.Button(master, text="Search", command=self.search_song)
        self.search_button.grid(row=0, column=2, padx=10, pady=10)

        # Text box to show search results
        self.result_text = tk.Text(master, height=10, width=50)
        self.result_text.grid(row=1, column=0, columnspan=3, padx=10, pady=10)
        # Hyperlink hint
        self.hint_label = tk.Label(master, text="Not the result you want?", fg="blue", cursor="hand2")
        self.hint_label.grid(row=2, column=0, columnspan=10, pady=10)
        self.hint_label.bind("<Button-1>", self.show_search_hint)
        # Download song section
        tk.Label(master, text="Song ID:").grid(row=3, column=0, padx=10, pady=10)
        self.song_id_entry = tk.Entry(master, width=30)
        self.song_id_entry.grid(row=3, column=1, padx=10, pady=10)
        self.download_button = tk.Button(master, text="Download", command=self.download_song)
        self.download_button.grid(row=3, column=2, padx=10, pady=10)

        # Save path section
        tk.Label(master, text="Save path:").grid(row=4, column=0, padx=10, pady=10)
        self.save_path_entry = tk.Entry(master, width=30)
        self.save_path_entry.grid(row=4, column=1, padx=10, pady=10)
        self.browse_button = tk.Button(master, text="Browse", command=self.browse_save_path)
        self.browse_button.grid(row=4, column=2, padx=10, pady=10)
        # Hot music recommendation section
        self.hot_music_button = tk.Button(master, text="Hot Songs", command=self.get_hot_music)
        self.hot_music_button.grid(row=5, column=0, padx=10, pady=10)

    def search_song(self):
        keyword = self.keyword_entry.get()
        details = self.get_music_details(keyword)
        self.result_text.delete(1.0, tk.END)  # clear the text box
        for detail in details:
            self.result_text.insert(tk.END, detail + "\n")

    def get_music_details(self, keyword):
        base_url = "https://www.gequbao.com/s/"
        search_url = f"{base_url}{keyword}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
        }
        
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()  # check if the request succeeded
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all matching <a> tags
            music_links = soup.select('div.card.mb-1 a.music-link.d-block')
            
            # Find all matching <span> tags
            music_titles = soup.select('span.text-primary.font-weight-bolder.music-title.d-md-inline-block.align-middle span')
            
            # Extract all href attributes, removing the '/music/' prefix
            hrefs = [link['href'].replace('/music/', '') for link in music_links]
            
            # Extract all song titles
            titles = [title.get_text(strip=True) for title in music_titles]
            
            # Combine titles and links
            results = [f"Title: {title}, ID: {href}" for title, href in zip(titles, hrefs)]
            
            return results
        except requests.RequestException as e:
            print(f"Request failed, please try again later: {e}")
            return []

    def download_song(self):
        in_id = self.song_id_entry.get()
        save_path = self.save_path_entry.get()
    
        # Check whether the save path exists
        if not save_path or not os.path.exists(save_path):
            tk.messagebox.showwarning("Warning", "Save path does not exist. Please choose a valid path.")
            return
    
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
        }
        url = f"https://www.gequbao.com/music/{in_id}"
    
        try:
            resp = requests.get(url, headers=headers, timeout=5)  # set timeout to 5 seconds
        except requests.exceptions.Timeout:
            tk.messagebox.showwarning("Warning", "Request timed out. Please check your network.")
            return
        except requests.exceptions.RequestException as e:
            tk.messagebox.showwarning("Warning", f"Request failed, please try again later: {e}")
            return
    

        link = "https://www.gequbao.com/api/play-url"
        data = {'id':'RFALUCRUAVZeSVsNV3NRXF5fF1pdAnhXU10DE1gPU3IaUVtRQlFNVndQUFpWRF9YUQ=='}
    
        try:
            response = requests.post(url=link, data=data, headers=headers, timeout=5)  # set timeout to 5 seconds
            json_data = response.json()
            play_url = json_data['data']['url']
        except requests.exceptions.Timeout:
            tk.messagebox.showwarning("Warning", "Request timed out. Please check your network.")
            return
        except requests.exceptions.RequestException as e:
            tk.messagebox.showwarning("Warning", f"Request failed, please try again later: {e}")
            return
    
        try:
            content = requests.get(play_url, headers=headers, timeout=5).content  # set timeout to 5 seconds
        except requests.exceptions.Timeout:
            tk.messagebox.showwarning("Warning", "Request timed out. Please check your network.")
            return
        except requests.exceptions.RequestException as e:
            tk.messagebox.showwarning("Warning", f"Request failed, please try again later: {e}")
            return
    
        # Save the song
        file_path = os.path.join(save_path, f"ruyuan.mp3")
        with open(file_path, 'wb') as f:
            f.write(content)
    
        self.result_text.insert(tk.END, f'Song downloaded successfully\n')

    def browse_save_path(self):
        path = filedialog.askdirectory()
        self.save_path_entry.delete(0, tk.END)
        self.save_path_entry.insert(0, path)

    def get_hot_music(self):
        # clear the text box
        self.result_text.delete(1.0, tk.END)

        base_url = "https://www.gequbao.com/hot-music/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
        }
        
        results = []
        for page in range(1, 7):
            url = f"{base_url}{page}"
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # check if the request succeeded
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all matching <td> tags (singers)
                singers = [td.get_text(strip=True) for td in soup.select('td.text-success')]
                
                # Find all matching <a> tags
                music_links = soup.select('a.text-info.font-weight-bold')
                titles = [a.get_text(strip=True) for a in music_links]
                hrefs = [a['href'].replace('/music/', '') for a in music_links]
                
                # Combine title, singer and ID
                page_results = [f"Title: {title}, Singer: {singer}, ID: {href}" for title, singer, href in zip(titles, singers, hrefs)]
                results.extend(page_results)
            except requests.RequestException as e:
                tk.messagebox.showwarning("Warning", f"Request failed, please try again later: {e}")
                return
        for result in results:
            self.result_text.insert(tk.END, result + "\n")

    def show_search_hint(self, event):
        tk.messagebox.showinfo("Search Hint", "Avoid special characters when searching. Enter the name and author together for better matching (e.g. ru yuan Wang Fei)")

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicDownloader(root)
    root.mainloop()
