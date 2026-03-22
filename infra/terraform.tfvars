# InfraLens Terraform Configuration

ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDDGF0WoikYON8jK7+K7CjOu/RJmCoASTv77VXZLEWjIpWkaV/K6oxfI0peA6+3CQRoaTuXtdSFxbwpe8y/RASfYNYedbzRndQM2RGcDnDx7vBClrVlZgJBU1m+kEIKWROMa9kTg6wwUHaJIjYkgGBXW7FDg8kxVrSJnlARdrd47J4ax6L3YG5CLrordusj8fgYIb6PTJn8jdj4gmHyC+J/g+p9cGFH7NZmJCqrs1z3kqcrQMxGT1HZ+gQkVnI3CJIOk++3eJWnRH1AhDM1s1dYJbJxftxms0eDEeWDb7z2oOqTELRVqJD0XvXQN54EZgQIosFmoqljLBhHYiKlybYsVzm7L9witEAjebD/GlvbGyNUFdNgOtubi5DjaBu68B3vpM8pd3L3NTUn3kZpGNDZlGJ/QeunTAFFkeWGm092C/ktlpG0NXEZkD559zR8orMlFt3RaScFfTDjD9Exgv41bjJk9qvrnD+D1onKL7jY4tlYDqvC+zXmLTmmC0h9lVjriJhTkQxvGrsT+qEJlQ67zVQ6J9ZTB7Z7NhXMRQUg767QXtwzZGNUAaNTaFAmShBMOqEDd+YToFfh8+3l77qc4hmna8vEMEr6kyTHpUU7ESlgguMGZeXHxC6WWwe1SIa4DCbljRaTit4fGX9nheVH7AefY1+EAL0I5dKH6XjcsQ== Shivani@silent-slayer"

# IPv4 address:
#   curl -4 ifconfig.me
allowed_ssh_cidr = "223.181.62.172/32"

aws_region    = "us-east-1"
project_name  = "infralens"

instance_type = "t3.micro"

enable_swap  = true
swap_size_gb = 2
