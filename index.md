# Spate Documentation


Easily create and run Workflows          |  
:-------------------------:|
![](images/spate_dash2.PNG)  |

### Table of Contents
1. [What is Spate?](#what-is-spate)
2. [Use Case](#use-case)
3. [How it Works](#how-it-works)
4. [Getting Started](#getting-started)
5. [Setting Up Your First Workflow](#setting-up-your-first-workflow)
6. [Development](#development)


### What is Spate?

Spate is a workflow and automation platform that allows anyone to quickly automate technical/business processes. It was first developed for the Information Security space however it can be used for any vertical. While automation is not always the answer, teams can use this platform to become more efficient and spend their precious (manual) time on other tasks.

### Use Case
(BEFORE) Let's look at a typical workflow for Incident Response (IR) for domain enrichment.
+ An alert fires and says "www. bad domain.com" is potentially a C2 channel
+ You have 5 security tools with data (endpoint, firewall, network, AD, etc.) that may be helpful
+ If you are lucky, you have a engineering team that has spent thousands of hours mapping data between the tools (lol)
+ You must log into the tools and perform manual searching and then worry about reporting (huge hassle)

(AFTER) With Spate, you can automate this pretty quickly.
+ An alert fires and says "www. bad domain.com" is potentially a C2 channel
+ You run the Spate Workflow and Spate queries and filters the data from the security tools
+ On success, it uploads the data to a Google Sheet
+ When complete, it sends a email to a mailing list with the report link

### How it Works

Spate is built on Flask (e.g. python framework) and leverages containerization (docker) for executing workflows. A "Workflow" is just a set of blocks that contain your automation tree. Users can use the drag-and-drop UI to add and connect Operators (blocks of logic) to their Workflow. Each Workflow has its own docker container.

Spate currently supports "API" and "CRON" Triggers. A trigger is "how" the Workflow is executed. For example, if your Workflow contains the "API" trigger, then users can visit a API endpoint to start the Workflow. The "CRON" trigger executes every X minutes and runs your Workflow. These two triggers will support the majority of your Workflows. Coming soon is a "FORM" trigger (basically lets you build a UI based form for input).

Users can add Operators to your Workflow and also edit the code. Everything is in "python" code. So if you understand Python, you can easily update/edit/add new Operators for your business process. 

### Getting Started
+ Make sure docker is installed (ubuntu works fine)
+ Clone the repo
+ Build the images with: `cp tools/build_all.sh $PWD && bash build_all.sh && rm build_all.sh`
+ Create base image with: `cd docker_image && docker build -t base-python .`
+ Start the containers: `docker-compose up -d postgres_db && docker-compose up -d spate_ui && docker-compose up -d spate_poller spate_cron spate_ingress`
+ Visit `http://your-ip`. Email is `admin@example.com` and password is `admin`
+ See the following "Setting Up Your First Workflow" section for your first Workflow

### Setting Up Your First Workflow

After the "Getting Started" section above, lets set up and execute a API based Workflow.

#### 1.) Select the "Graph" icon on "Default Workflow"
<img src="images/spate_step1.PNG" alt="" class="inline"/>

#### 2.) Drop the "API Ingress" and "Basic Operator" (under Actions) and connect them. After, hit the "Refresh" button at the bottom right (IMPORTANT)
<img src="images/spate_step2.PNG" alt="" class="inline"/>

#### 3.) Visit the API endpoint (port 8080) to start the Workflow
<img src="images/spate_step3.PNG" alt="" class="inline"/>

#### 4.) Go back to the Workflows page and select the "Results" icon
<img src="images/spate_step4.PNG" alt="" class="inline"/>

#### 5.) View the results of your Workflow
<img src="images/spate_step5.PNG" alt="" class="inline"/>


### Development

##### Stop docker images
`docker-compose down`

##### Create base image
`cd docker_image && docker build -t base-python .`

##### Build docker images
`cp tools/build_all.sh $PWD && bash build_all.sh && rm build_all.sh`

##### Authentication
`admin@example.com:admin`

##### Start docker images
`docker-compose up -d postgres_db && docker-compose up -d spate_ui && docker-compose up -d spate_poller spate_cron spate_ingress`

##### Docker debugging
Your 'docker ps' command should look something like this (4 containers with spate_). Check the logs of the containers for errors.

<img src="images/spate_debug.PNG" alt="" class="inline"/>
