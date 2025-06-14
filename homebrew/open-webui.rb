class OpenWebui < Formula
  include Language::Python::Virtualenv

  desc "Extensible, self-hosted interface for AI that adapts to your workflow"
  homepage "https://github.com/open-webui/open-webui"
  url "https://files.pythonhosted.org/packages/13/3f/00c884826aca5d0c9a330b6d1ebc2d4b8d10d67e0cd11b516ecb90a7685a/open_webui-0.6.14.tar.gz"
  sha256 "4e775912a722b05feb91845efe039f740e4c26d04bb37ba455b7f66ddd41d1bc"
  license "MIT"

  depends_on "node@22" => :build
  depends_on "python@3.12"

  def install
    # Create virtual environment with pip
    system "python3.12", "-m", "venv", libexec
    
    # Install open-webui and all its dependencies
    system libexec/"bin/pip", "install", "--upgrade", "pip"
    system libexec/"bin/pip", "install", "open-webui==#{version}"
    
    # Create wrapper script
    (bin/"open-webui").write_env_script libexec/"bin/open-webui", {}
  end

  test do
    assert_match "open-webui", shell_output("#{bin}/open-webui --help")
  end
end
