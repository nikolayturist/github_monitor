GITHUB request collector project

1. Required modules are in requirements.txt
2. For launching pull request collector create following configuration file:
    - connection_config_local.json
    
    with following content:
   
    `{
      "github": {
        "github_token": "<git hub api key if any>" 
      },
      "db": {
          "username": "<oracle_user_name>",
          "password": "<oracle_db_password>",
          "host": "localhost",
          "port": 1521,
          "service": "orclpdb"
        },
      "machines_cluster": ["IPADDR_1", "IPADDR_2", ...]
    }`
   
3. Launch collection using pullrequest_monitor/pull_monitor.py
4. Analysis will answer on following questions:
   - What is the min, average and max time to merge a pull request? 
   - What are the top 3 files that are changed most often in pull requests?
5. For analysis several options can be user:
    - SQL queries
    - python script with pandas/numpy
    - python script which can be launched on multiple machines using dispy library 