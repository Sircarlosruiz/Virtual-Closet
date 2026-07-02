terraform {
  backend "s3" {
    bucket         = "virtualcloset-tfstate"
    key            = "staging/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "virtualcloset-tfstate-lock"
  }
}
