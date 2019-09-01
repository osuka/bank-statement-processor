# Reference Visual Studio Code container for this project

This can help set everything up without having to install anything locally.

Visual Studio Code and its extensions run inside a docker container, using
code's remote server.

This can be used to

* Isolate all dependencies and extensions for a particular project to not pollute your machine
* Optionally, have everything run in a remote machine so you only need a barebones client with visual studio code.

## Key files

1. *.devcontainer/Dockerfile* - defines a base image in which the tools will be run (python, pylint)
2. *.devcontainer/devcontainer.json* - defines the vscode environment that will run in the container
     This defines all extensions and folder mappings to the source code.
3. *../yourname.code-worspace* - you can optionally create this as a workspace file and define DOCKER_HOST in there to
     have it work remotely instead of in the local machine

## Step by step instructions

* Install Visual Studio Code
* Install the Docker extension in Visual Studio Code
* Install the Remote Development (by Microsoft) extension in Visual Studio Code
* git checkout this repository
* Open the repo folder in visual studio code
* Ignore (for now) the message about opening the remote container.
* If you are going to be running it remotely, click on "File/Save Workspace As...", then go to "Preferences/Settings" and search for DOCKER_HOST and once in there type the host address of your target machine, plus port.

* Reopen the folder and this time, when prompted, accept launching the workspace inside a container.

Visual studio will relaunch and now it will use the extensions defined in the file `.devcontainer/devcontainer.json` and it will have available all the services/applications the Dockerfile sets as base installation. You can install more extensions manually using Visual Studio or add packages with `apt-get` but to make those changes permanent you need to modify the files and rebuild the container (log into your server and remove the old container and image as they are reused for future launches).

> Note: an easy way to get access to a locked docker (one that only listens to a local socket) is to create a tunnel: `ssh -NL 127.0.0.1:23750:/var/run/docker.sock YOURUSER@YOURREMOTEHOST`) and then in workspace settings define DOCKER_HOST to point docker to the tunnel `{ "settings": { "docker.host": "127.0.0.1:23750" } }`
> Alternative way to launch the remote connection: Press ctrl-alt-p and select _Remote-Containers: Reopen folder in container_ to do the same
