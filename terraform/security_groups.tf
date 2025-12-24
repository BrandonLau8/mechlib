
# Virtual Firewall
#  This means your mechlib EC2 instance will only allow the traffic defined in the security group rules.
#  Without this security group, your instance would be exposed to the internet with no firewall protection.
resource "aws_security_group" "mechlib" {
  name        = "mechlib-${var.environment}"
  description = "Security group for mechlib EC2"

  # Inbound Traffic
  # SSH access (port 22): Allows you to connect to the server from your admin IP address
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip]  # Your office IP
  }

  # pgbouncer (port 6432): Allows your application server to connect to the PostgreSQL connection pooler
  ingress {
    from_port   = 6432
    to_port     = 6432
    protocol    = "tcp"
    cidr_blocks = [var.app_server_ip]
  }

  # Outbound Traffic
  # EC2 instance to make any outbound connections (any port): for updates, downloading packages, etc.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}