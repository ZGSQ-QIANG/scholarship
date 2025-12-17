import requests

my_doi="10.1145/3626772.3657813"

print("正在尝试连接CrossRef ...")

url=f"https://api.crossref.org/works/{my_doi}"
response=requests.get(url)

data=response.json()

print("标题为：",data['message']['title'][0])
print("出版商是：",data['message']['publisher'])