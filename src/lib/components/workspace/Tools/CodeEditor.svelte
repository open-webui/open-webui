<script lang="ts">
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let value = '';

	let codeEditor;
	let boilerplate = `from datetime import datetime
import requests
import os

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints
    # Use Sphinx-style docstrings to document your tools, they will be used for generating tools specifications
    # Please refer to function_calling_filter_pipeline.py file from pipelines project for an example

    def get_environment_variable(self, variable_name: str) -> str:
        """
        Get the value of an environment variable.
        :param variable_name: The name of the environment variable.
        :return: The value of the environment variable or a message if it doesn't exist.
        """
        value = os.getenv(variable_name)
        if value is not None:
            return f"The value of the environment variable '{variable_name}' is '{value}'"
        else:
            return f"The environment variable '{variable_name}' does not exist."

    def get_current_time(self) -> str:
        """
        Get the current time.
        :return: The current time.
        """

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        return f"Current Time = {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

`;

	export const formatHandler = async () => {
		if (codeEditor) {
			return await codeEditor.formatPythonCodeHandler();
		}
		return false;
	};
</script>

<CodeEditor
	bind:value
	{boilerplate}
	bind:this={codeEditor}
	on:save={() => {
		dispatch('save');
	}}
/>
