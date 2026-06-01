1、macos/linux上设置max-old-space-size
	vi ~/.bashrc或.zshrc添加环境变量
	`export NODE_OPTIONS="--max-old-space-size=16384"`
	然后source .bashrc/.zshrc