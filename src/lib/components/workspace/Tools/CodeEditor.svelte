<script lang="ts">
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let value = '';

	let codeEditor;
	let boilerplate = `import os
import requests
from datetime import datetime


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
            return (
                f"The value of the environment variable '{variable_name}' is '{value}'"
            )
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

    def get_current_weather(self, city: str) -> str:
        """
        Get the current weather for a given city.
        :param city: The name of the city to get the weather for.
        :return: The current weather information or an error message.
        """
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
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
