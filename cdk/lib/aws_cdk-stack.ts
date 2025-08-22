import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatch_actions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambda_python_alpha from "@aws-cdk/aws-lambda-python-alpha";
import * as scheduler from "aws-cdk-lib/aws-scheduler";
import * as scheduler_targets from "aws-cdk-lib/aws-scheduler-targets";
import * as sns from "aws-cdk-lib/aws-sns";

export class DidacticEurekaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const layer = new lambda_python_alpha.PythonLayerVersion(this, "layer", {
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      entry: "../layer",
    });

    const update_data = new lambda_python_alpha.PythonFunction(this, "update_data", {
      entry: "../lambda",
      handler: "handler",
      index: "update_data.py",
      layers: [layer],
      loggingFormat: lambda.LoggingFormat.JSON,
      runtime: lambda.Runtime.PYTHON_3_13,
      timeout: cdk.Duration.seconds(10),
      tracing: lambda.Tracing.ACTIVE,
    });

    update_data.role!.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchFullAccessV2"));

    const lambda_scheduler = new scheduler.Schedule(this, "scheduler", {
      schedule: scheduler.ScheduleExpression.cron({
        minute: "0",
        hour: "*/6",
        month: "*",
        weekDay: "1-5",
      }),
      target: new scheduler_targets.LambdaInvoke(update_data),
      timeWindow: scheduler.TimeWindow.flexible(cdk.Duration.minutes(15)),
    });

    const topic = new sns.Topic(this, "topic");

    // subscription must be added manually

    const alarm = new cloudwatch.Alarm(this, "alarm", {
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      evaluationPeriods: 1,
      metric: update_data.metricErrors({ statistic: "Minimum" }),
      threshold: 0,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    alarm.addAlarmAction(new cloudwatch_actions.SnsAction(topic));
  }
}
