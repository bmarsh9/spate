<p align="center">
  <img height="120px" src="https://github.com/bmarsh9/spate/raw/de65a206015f1119db5981f21fc3974b8a8c8c7f/app/static/img/spate_full.PNG" alt="Logo"/>
</p>

Discord: https://discord.gg/9unhWAqadg  
Official Integrations: https://github.com/bmarsh9/spate-operators

### [Read the documentation to get started](https://bmarsh9.github.io/spate/)

View Results           |  Create Workflows
:-------------------------:|:-------------------------:
![](https://github.com/bmarsh9/spate/blob/7947fa3e00af25916b7c551e787ea58e7c133a70/app/static/img/spate_dash1.PNG)  |  ![](https://github.com/bmarsh9/spate/blob/7947fa3e00af25916b7c551e787ea58e7c133a70/app/static/img/spate_dash2.PNG)


### Check out a quick example!  
The following workflow will consume a URL and return a quick summary of the article. We will set up a workflow and execute the workflow via the Spate CLI (which just hits the HTTP API endpoint of the workflow).

https://user-images.githubusercontent.com/26391921/159962525-d85df2aa-52a4-48e7-9fd8-8cd52ddd37bb.mp4


### Try out the live API endpoint. 

This endpoint hosted by spate will read the `name` parameter and say hello!  

```
# First send a query to start the workflow
curl -k "https://spate.darkbanner.com/api/v1/endpoints/8cab12277c?name=tom"

# Now query the callback URL. The UUID will be different for you
curl -k "https://spate.darkbanner.com/api/v1/executions/3b8c9444239d4c52801ffb1f01724d41"

# The return_value key will show the returned message!
```
