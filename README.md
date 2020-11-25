- create virtual environment  
`python3 -m venv .`

- activate virtual environment  
`source ./bin/activate`

- install requirements
`pip install -r requirements.txt`

- setup queries in `queries.csv` file  
it's better to ensure precision to specify country  
```
location, business
13083 US, auction house
new york US, pizza restaurant
berlin, night clubs
```

- run queries  
`python3 search.py`

- results will be saved to csv file by the end of each query script run  

- support: leovictorsr@gmail.com