# pyright-remote
Instructions on setting up pyright on remote server

# Description

This repo contains guide on setting [Microsoft's pyright](https://github.com/microsoft/pyright "pyright's github")
lsp server on a remote dev machine (e.g. the machine where the source code is hosted and modified)
and using it on local machine (e.g. the machine where an editor is launched and used) as emacs's
[eglot](https://github.com/joaotavora/eglot "eglot") backend.

The steps described here assume that both your remote and local machine are running something nix-like (e.g. mac, linux, etc.).
Other operation systems are likely may be set up using this approach as well, but will require some modifications. I've no experience with that.


# Step 1: Getting pyright

This section describes installing pyright the way I recommend to do it for our purposes.
There multiple other ways, you can use them, if you want.

Pyright is implemented using [typescript](https://en.wikipedia.org/wiki/TypeScript "wikipedia")
and runs as a [node.js](https://en.wikipedia.org/wiki/Node.js "wikipedia") server application.
To manage node versions I use [nvm](https://github.com/nvm-sh/nvm "nvm"). 

There is a pip package called `pyright` that installs pyright which I don't recommend to use.

[Install](https://github.com/nvm-sh/nvm "nvm") it as described in the doc.
When your nvm installation works, install node. Node version 16 worked for me, but not the later ones. Install it by running: `nvm install 16`
This will install the latest available (`v16.17.1` at the moment of writing this lines. Would be used further as an example)
version of node.js v16 and create appropriate folder `~/.nvm/versions/node/v16.17.1/`.
You can check it up by running `~/.nvm/versions/node/v16.17.1/bin/node -v` which should print you `v16.17.1`.
It should also provide you with an installed npm [node.js](https://en.wikipedia.org/wiki/Npm_(software) "wikipedia") in the same directory.
Let's install pyright into a separate directory. Run `mkdir .pyright-install/ ; cd .pyright-install/` and then
`/.nvm/versions/node/v16.17.1/bin/npm install pyright`.
If everything happened normally, you must be able to run pyright
`~/.nvm/versions/node/v16.17.1/bin/node node_modules/.bin/pyright`
which does nothing since it can not find any source code.

# Step 2: creating a pyright wrapper script

In the directory `.pyright-install/` created on the previous step create files, one for pyright, one for pyright-langserver.

pyright.sh:
```
PATH="$HOME/.nvm/versions/node/v16.17.1/bin" exec node $HOME/.pyright-install/node_modules/.bin/pyright $@
```

pyright-langserver.sh:
```
PATH="$HOME/.nvm/versions/node/v16.17.1/bin" exec node $HOME/.pyright-install/node_modules/.bin/pyright-langserver $@
```
We intentionally limit PATH variable. # TODO
Symbols `$@` in this sh script mean that all commandline arguments provided to this script will be propagated to pyright.
Make both files executable by running `chmod +x pyright.sh ; chmod +x pyright-langserver.sh`

Verify that `pyright.sh` runs successfully by running `$HOME/.pyright-install/pyright.sh` from any directory. You must see `Searching for source files` 
line, most likely followed by `No source files found.`. 


# Step 3: Making pyright working
After the above step you must be able to run pyright with the output looking like
```
Searching for source files
No source files found.
```

Chdir to the root of your python project, refer to pyright's cli and 
[cli](https://github.com/microsoft/pyright/blob/main/docs/command-line.md#pyright-command-line-options "doc")
and
[configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md "doc")
documentation, and create `pyrightconfig.json` file.
Check your project by running `$HOME/.pyright-install/pyright.sh --verbose -p pyrightconfig.json`.
Checkout the example project and config file in this repo FIXME. The output should contain error
```
greeter.py:12:16 - error: Operator "+" not supported for types "str" and "int"
```
This is essential that you make pyright commandline version working before moving forward to using pyright-langserver.
The latter is extremely hard to troubleshoot.

# Step 3: checking eglot.
I assume you have [eglot] (https://github.com/joaotavora/eglot "github") installed on your local emacs. 
On local machine open a python file of your project on remote machine and run `M-x eglot`.
You should get a prompt
``` text
[eglot] Sorry, couldn't guess for `python-mode'!
Enter program to execute (or <host>:<port>): 
```

# Step 4: connecti eglot to pyright
The problem with pyright-langserver is that it acts like a tcp-client, not the server. When it starts, and all the time it's running,
it requires someone to read another side of the socket.
We solve this problem by having a simple intermediate proxy, that passes all messages from pyright-langserver to eglot, and vise-versa.
Therefore, it uses two ports, the `server port` that pyright-langserver binds to, and `client port` which eglot will bind two.
I'll use 9999 as server port and 10000 as client port along this guide.

Start the proxy server on your remote machine.
``` shell
python tcp_pipe.py  --server-port 9999 --client-port 10000
```

Start pyright-langserver on your remote machine.
``` shell
 ~/.pyright-install/pyright-langserver.sh --verbose  -p pyrightconfig.good.json  --socket=9999
 ```

Open an ssh tunnel from your local machine to your remote machine.
```
ssh -L 10000:localhost:10000 your.remote.machine
```
Open a file of your python project in Emacs, run `M-x eglot`, when prompted to enter host and port, enter `localhost:10000`

It should work.

# Step 5: [May be optional] setup projectile project root

Eglot uses project.el to bind files to projects, and projects are bound to an lsp-server.
I use [doom emacs](https://github.com/doomemacs/doomemacs "github") which uses projectile.el project management package.

The solution to bind them together was found at 
https://github.com/bbatsov/projectile/issues/1591#issuecomment-903042091

I put this code to my config

``` emacs-lisp

(require 'cl-lib)

(cl-defmethod project-root ((project (head projectile)))
  (cdr project))

(cl-defmethod project-files ((project (head projectile)) &optional dirs)
  (let ((root (project-root project)))
    ;; make paths absolute and ignore the optional dirs argument,
    ;; see https://github.com/bbatsov/projectile/issues/1591#issuecomment-896423965
    (mapcar (lambda (f)
              (expand-file-name f root))
            (projectile-project-files root))))

(defun project-projectile (dir)
  "Return projectile project of form ('projectile . ROOT-DIR) for DIR"
  (let ((root (projectile-project-root dir)))
    (when root
      (cons 'projectile root))))

;; Doom-emacs scpecific way to ebable it
(after! projectile
  (add-hook 'project-find-functions #'project-projectile))

```

# Step 6: [Even mode likely optional] setup projectile project root

The second problem I had was project identification.
Projectile wasn't able to identify my code as a project.
So, added a specific type of project identified by an empty file `.projectile-my-python`
put in the project root.


``` emacs-lisp
(after! projectile
    (setq projectile-project-root-files '())
    (projectile-register-project-type 'my-python '(".projectile-my-python")
                                      :project-file ".projectile-my-python")
)
```

After this point project identification worked fine for me.

# Step 7: Saving port settings specific to the project

Emacs has [dir-locals](https://www.gnu.org/software/emacs/manual/html_node/emacs/Directory-Variables.html)
feature that allows to set specific variables on opened files by reading specific `.dir-locals.el` file.
Note that `.dir-locals.el` doesn't contain elisp code, it would be dangerous, but rather variable's values.

I put this file in the root of my project on remote host, near to `.projectile-my-python`

``` emacs-lisp
((python-mode . (
    (eglot-server-programs    . ((python-mode "localhost" 55601)))
  )
))

((nil . (
    (projectile-project-name . "my-remote-python")
  )
))

```

# Finally

That's all. That's how I use pyright with emacs. The langserver-python and proxy processes are kept on remote server up and running,
and I emacs connects to the proxy, when I open a file in the project. I have to keep ssh tunnel running, I still don't know any working solution for this.
Sometimes manual reconnect using `M-x eglot-reconnect` or `M-x eglot` is required.

# Multiple clients support

Currently, tcp proxy supports only one client at a time.
However, editing one project from different editors may be a reasonable thing to do.
Adding support for multiple clients to a proxy to parse each incoming json-rpc request.
In consists of a simple `Content-Length` header and json body.
Each request has an id, and server's response contains an id of the request server is responding to.
In practice, id's are increasing integer numbers starting from 1, so they can easily intersect in requests from different clients.

After parsing the request proxy would be able to generate some unique request id, and replace it's original request id.
For each new request id, proxy must remember it's original client.
After recieving a response from server, it must determine which client should recieve this response.

This support is currently not planned to be add in the future.

# Other clients

This guide basically consists of two parts: setting up pyright-langserver + proxy, and setting up emacs + eglot.
If you have an instruction for other editors and willing to add it here, open an issue or make a PR, or both.

