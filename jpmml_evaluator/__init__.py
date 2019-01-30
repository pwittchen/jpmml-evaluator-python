#!/usr/bin/env python

from pandas import DataFrame
from py4j.java_collections import JavaMap
from py4j.java_gateway import JavaGateway

import os
import pkg_resources

from .metadata import __copyright__, __license__, __version__

class JavaObject(object):

	def __init__(self, gateway):
		self.gateway = gateway

	def _jvm(self):
		return self.gateway.jvm

class ModelField(JavaObject):

	def __init__(self, gateway, javaModelField):
		super(ModelField, self).__init__(gateway)
		self.javaModelField = javaModelField
		# Transform Java objects to Python strings
		self.name = javaModelField.getName().getValue()
		self.dataType = javaModelField.getDataType().value()
		self.opType = javaModelField.getOpType().value()

	def __str__(self):
		return self.javaModelField.toString()

	def getName(self):
		return self.name

	def getDataType(self):
		return self.dataType

	def getOpType(self):
		return self.opType

def _initModelFields(gateway, javaModelFields):
	return [ModelField(gateway, javaModelField) for javaModelField in javaModelFields]

class Evaluator(JavaObject):

	def __init__(self, gateway, javaEvaluator):
		super(Evaluator, self).__init__(gateway)
		self.javaEvaluator = javaEvaluator

	def verify(self):
		self.javaEvaluator.verify()
		return self

	def getInputFields(self):
		if not hasattr(self, "inputFields"):
			self.inputFields = _initModelFields(self.gateway, self.javaEvaluator.getInputFields())
		return self.inputFields

	def getTargetFields(self):
		if not hasattr(self, "targetFields"):
			self.targetFields = _initModelFields(self.gateway, self.javaEvaluator.getTargetFields())
		return self.targetFields

	def getOutputFields(self):
		if not hasattr(self, "outputFields"):
			self.outputFields = _initModelFields(self.gateway, self.javaEvaluator.getOutputFields())
		return self.outputFields

	def evaluate(self, arguments):
		jvm = self._jvm()
		javaArguments = jvm.java.util.LinkedHashMap()
		for k, v in arguments.items():
			javaArguments.put(jvm.org.dmg.pmml.FieldName.create(k), v)
		javaResults = self.javaEvaluator.evaluate(javaArguments)
		results = jvm.org.jpmml.evaluator.EvaluatorUtil.decode(javaResults)
		return results

	def evaluateAll(self, arguments_df):
		argument_records = arguments_df.to_dict(orient = "records")
		result_records = []
		for argument_record in argument_records:
			result_record = self.evaluate(argument_record)
			result_records.append(result_record)
		return DataFrame.from_records(result_records)

class BaseModelEvaluatorBuilder(JavaObject):

	def __init__(self, gateway, javaModelEvaluatorBuilder):
		super(BaseModelEvaluatorBuilder, self).__init__(gateway)
		self.javaModelEvaluatorBuilder = javaModelEvaluatorBuilder

	def build(self):
		javaEvaluator = self.javaModelEvaluatorBuilder.build()
		return Evaluator(self.gateway, javaEvaluator)

class ModelEvaluatorBuilder(BaseModelEvaluatorBuilder):

	def __init__(self, gateway, javaPMML):
		javaModelEvaluatorBuilder = gateway.jvm.org.jpmml.evaluator.ModelEvaluatorBuilder(javaPMML)
		super(ModelEvaluatorBuilder, self).__init__(gateway, javaModelEvaluatorBuilder)

class LoadingModelEvaluatorBuilder(BaseModelEvaluatorBuilder):

	def __init__(self, gateway):
		javaModelEvaluatorBuilder = gateway.jvm.org.jpmml.evaluator.LoadingModelEvaluatorBuilder()
		super(LoadingModelEvaluatorBuilder, self).__init__(gateway, javaModelEvaluatorBuilder)

	def setLocatable(self, locatable = False):
		self.javaModelEvaluatorBuilder.setLocatable(locatable)
		return self

	def setDefaultVisitorBattery(self):
		jvm = self._jvm()
		visitors = jvm.org.jpmml.evaluator.DefaultVisitorBattery()
		self.javaModelEvaluatorBuilder.setVisitors(visitors)
		return self

	def loadFile(self, path):
		jvm = self._jvm()
		self.javaModelEvaluatorBuilder.load(jvm.java.io.File(path))
		return self

def launch_gateway(user_classpath = []):
	return JavaGateway.launch_gateway(classpath = os.pathsep.join(_classpath(user_classpath)))

def _classpath(user_classpath):
	return _package_classpath() + user_classpath

def _package_classpath():
	jars = []
	resources = pkg_resources.resource_listdir("jpmml_evaluator.resources", "")
	for resource in resources:
		if resource.endswith(".jar"):
			jars.append(pkg_resources.resource_filename("jpmml_evaluator.resources", resource))
	return jars
