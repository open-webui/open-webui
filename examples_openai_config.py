#!/usr/bin/env python3
"""
Example script demonstrating OpenAI configuration management

This script shows various ways to interact with OpenAI configurations
in Open WebUI.
"""

from openai_config_manager import OpenAIConfigManager


def example_basic_operations():
    """Demonstrate basic CRUD operations"""
    print("=== Basic Operations ===\n")

    manager = OpenAIConfigManager()

    # List existing configurations
    print("1. Listing existing configurations:")
    configs = manager.list()
    if configs:
        for config_id, config in configs.items():
            print(f"   {config_id}: {config.get('name', 'Unknown')}")
    else:
        print("   No configurations found")
    print()

    # Add a new configuration
    print("2. Adding a new configuration:")
    try:
        manager.add(
            config_id='0',
            name='OpenAI Official',
            base_url='https://api.openai.com/v1',
            api_key='sk-example-key-replace-with-real-key',
            model='gpt-4'
        )
        print("   ✓ Configuration added successfully")
    except ValueError as e:
        print(f"   ℹ Configuration already exists: {e}")
    print()

    # Get a specific configuration
    print("3. Getting configuration '0':")
    config = manager.get('0')
    if config:
        print(f"   Name: {config.get('name')}")
        print(f"   Base URL: {config.get('base_url')}")
        print(f"   Model: {config.get('model')}")
    else:
        print("   Configuration not found")
    print()

    # Update a configuration
    print("4. Updating configuration '0':")
    try:
        manager.update(
            config_id='0',
            model='gpt-4-turbo'
        )
        print("   ✓ Configuration updated successfully")
    except ValueError as e:
        print(f"   ✗ Update failed: {e}")
    print()


def example_batch_operations():
    """Demonstrate batch operations"""
    print("=== Batch Operations ===\n")

    manager = OpenAIConfigManager()

    providers = [
        {
            'id': '0',
            'name': 'OpenAI Official',
            'base_url': 'https://api.openai.com/v1',
            'api_key': 'sk-openai-key',
            'model': 'gpt-4'
        },
        {
            'id': '1',
            'name': 'Azure OpenAI',
            'base_url': 'https://your-resource.openai.azure.com',
            'api_key': 'azure-key',
            'model': 'gpt-4-32k'
        },
        {
            'id': '2',
            'name': 'Custom Provider',
            'base_url': 'https://custom-api.example.com',
            'api_key': 'custom-key',
            'model': 'custom-model'
        }
    ]

    print("Adding multiple configurations:")
    for provider in providers:
        try:
            manager.add(
                config_id=provider['id'],
                name=provider['name'],
                base_url=provider['base_url'],
                api_key=provider['api_key'],
                model=provider['model']
            )
            print(f"   ✓ Added: {provider['name']}")
        except ValueError:
            print(f"   ℹ Already exists: {provider['name']}")
    print()


def example_advanced_features():
    """Demonstrate advanced features"""
    print("=== Advanced Features ===\n")

    manager = OpenAIConfigManager()

    # Get all configurations with full details
    print("1. Getting all configurations with full details:")
    all_configs = manager.get_all_details()
    for config_id, config in all_configs.items():
        print(f"   ID {config_id}:")
        print(f"     Name: {config.get('name')}")
        print(f"     URL: {config.get('base_url')}")
        # Mask the API key for security
        api_key = config.get('api_key', '')
        if api_key:
            masked_key = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else '***'
            print(f"     Key: {masked_key}")
        print()

    # Check if OpenAI API is enabled
    print("2. Checking if OpenAI API is enabled:")
    is_enabled = manager.is_openai_api_enabled()
    print(f"   OpenAI API enabled: {is_enabled}")
    print()

    # Enable OpenAI API
    print("3. Ensuring OpenAI API is enabled:")
    manager.enable_openai_api(True)
    print("   ✓ OpenAI API enabled")
    print()


def example_cleanup():
    """Demonstrate cleanup operations"""
    print("=== Cleanup Operations ===\n")

    manager = OpenAIConfigManager()

    print("WARNING: This will remove example configurations.")
    print("Comment out this function call if you don't want to remove configs.")
    print()

    # Uncomment the following to actually remove configurations
    # configs_to_remove = ['0', '1', '2']
    # for config_id in configs_to_remove:
    #     try:
    #         manager.remove(config_id)
    #         print(f"   ✓ Removed configuration '{config_id}'")
    #     except ValueError:
    #         print(f"   ℹ Configuration '{config_id}' not found")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("OpenAI Configuration Management Examples")
    print("="*60 + "\n")

    try:
        example_basic_operations()
        print("\n" + "-"*60 + "\n")

        example_batch_operations()
        print("\n" + "-"*60 + "\n")

        example_advanced_features()
        print("\n" + "-"*60 + "\n")

        # Uncomment to run cleanup
        # example_cleanup()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()

