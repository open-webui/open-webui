# Testing signup

How to test sign up with a local Minikube setup.


## Helicopter view

1. Pick startpage option
2. Choose "signup" in the overlay
3. Open new tab and goto http://gpt.local/auth
4. At the new tab open the dev tools and break at a router breakpoint


## Detailed steps

### Add breakpoint

1. Open dev tools at Source panel
2. Search `routes/+layout.svelte`
3. Add Breakpoint at `if (localStorage.token) {`

With this breakpoint you'll stop before Open WebUI can complete the authentication. This is done to intercept the login and authenticate the user without running code for the signup completion.

### Goto the startpage (explore)

1. Open startpage
2. Select a sample prompt (note: once fake signup and login is completed you're not supposed to be back in chat)
3. In the overlay pick "Signup"
4. **Observation:** you'll land at https://dummy-shop.local/gpt

### Login in a new tab

1. Open 
2. Login at Keycloak
3. Land at http://gpt.local/auth
4. **Observation:** you'll stop at the breakpoint
5. Run the following code in the **Console** and then close the tab:

```
localStorage.setItem("token", location.hash.substring(1).split('=')[1])
```

### In the original open http://gpt.local/

1. In the original tab open http://gpt.local/
2. If you stop at the breakpoint, just continue
3. **Observation:** you should be logged in with **no chat started**

