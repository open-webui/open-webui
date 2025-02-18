data "aws_ssm_parameter" "oidc_provider_arn" {
  name = "/eks/infra/web/oidc-provider-arn"
}

locals {
  oidc_bits   = split("/", data.aws_ssm_parameter.oidc_provider_arn.value)
  oidc_prefix = join("/", slice(local.oidc_bits, 1, length(local.oidc_bits)))
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = [
      "sts:AssumeRoleWithWebIdentity",
    ]

    principals {
      type        = "Federated"
      identifiers = [data.aws_ssm_parameter.oidc_provider_arn.value]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_prefix}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_prefix}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }
  }
}

resource "aws_iam_role" "service_account" {
  name                 = "eks-sa-${var.service_account_name}"
  description          = "ServiceAccount IAM role for ${var.service_account_name}"
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  permissions_boundary = var.boundary_policy_arn

  inline_policy {
    name   = "service_account"
    policy = data.aws_iam_policy_document.service_account.json
  }
}

data "aws_iam_policy_document" "service_account" {
  statement {
    actions = ["s3:*"]
    resources = [
      "arn:aws:s3:::f.3dhubs.com",
      "arn:aws:s3:::f.3dhubs.com/*",
    ]
  }
}
