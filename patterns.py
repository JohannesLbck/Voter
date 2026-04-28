## File for processing templates with the information from the constraints

from xml.sax.saxutils import escape


_XML_ATTR_ESCAPES = {'"': '&quot;', "'": '&apos;'}


_MAX_EXEC_TIME_TEMPLATE = """<testset xmlns="http://cpee.org/ns/properties/2.0">
    <executionhandler>ruby</executionhandler>
    <dataelements/>
    <endpoints>
        <timeout>https-post://cpee.org/services/timeout.php</timeout>
        <subprocess>https-post://cpee.org/flow/start/url/</subprocess>
        <alternative>__ALTERNATIVE_URL__</alternative>
      <receive>https-get://cpee.org/ing/correlators/message/receive/</receive>
    </endpoints>
    <attributes>
        <guarded>none</guarded>
        <info>MaxExecTime</info>
        <modeltype>CPEE</modeltype>
        <theme>extended</theme>
        <creator>Christine Ashcreek</creator>
        <guarded_id/>
        <author>Christine Ashcreek</author>
        <model_uuid>9c4b8c32-18ed-4112-935e-fe0ee9c88697</model_uuid>
        <model_version/>
        <design_dir>Staff.dir/Loebbi.dir/Voting.dir/Patterns.dir</design_dir>
        <design_stage>development</design_stage>
    </attributes>
    <description>
        <description xmlns="http://cpee.org/ns/description/1.0">
        <parallel eid="e1" wait="-1" cancel="last">
          <parallel_branch>
            <call id="a1" endpoint="timeout">
              <parameters>
                <label>Max Time</label>
                <color/>
                <arguments>
                  <timeout>__MAX_TIME__</timeout>
                  <data/>
                </arguments>
              </parameters>
              <annotations>
                <_generic/>
                <_logging_behavior>
                  <_exclude>false</_exclude>
                  <_include>false</_include>
                </_logging_behavior>
                <_timing>
                  <_timing_weight/>
                  <_timing_avg/>
                  <explanations/>
                </_timing>
                <_shifting>
                  <_shifting_type>Duration</_shifting_type>
                </_shifting>
                <_context_data_analysis>
                  <probes/>
                  <ips/>
                </_context_data_analysis>
                <report>
                  <url/>
                </report>
                <_notes>
                  <_notes_general/>
                </_notes>
              </annotations>
              <documentation>
                <input/>
                <output/>
                <implementation>
                  <description/>
                </implementation>
              </documentation>
            </call>
            <call id="a2" endpoint="alternative">
              <parameters>
                <label>Alternative</label>
                <color/>
                <method>:post</method>
                <arguments/>
              </parameters>
              <annotations>
                <_generic/>
                <_logging_behavior>
                  <_exclude>false</_exclude>
                  <_include>false</_include>
                </_logging_behavior>
                <_timing>
                  <_timing_weight/>
                  <_timing_avg/>
                  <explanations/>
                </_timing>
                <_shifting>
                  <_shifting_type>Duration</_shifting_type>
                </_shifting>
                <_context_data_analysis>
                  <probes/>
                  <ips/>
                </_context_data_analysis>
                <report>
                  <url/>
                </report>
                <_notes>
                  <_notes_general/>
                </_notes>
              </annotations>
              <documentation>
                <input/>
                <output/>
                <implementation>
                  <description/>
                </implementation>
              </documentation>
            </call>
          </parallel_branch>
          <parallel_branch>
            <call id="a3" endpoint="receive">
              <parameters>
                <label/>
                <color/>
                <arguments>
                  <id>__TARGET__</id>
                  <ttl>0</ttl>
                  <delete>true</delete>
                </arguments>
              </parameters>
              <code>
                <signal>false</signal>
                <prepare/>
                <finalize output="result"/>
                <update output="result"/>
                <rescue output="result"/>
              </code>
              <annotations>
                <_generic/>
                <_logging_behavior>
                  <_exclude>false</_exclude>
                  <_include>false</_include>
                </_logging_behavior>
                <_timing>
                  <_timing_weight/>
                  <_timing_avg/>
                  <explanations/>
                </_timing>
                <_shifting>
                  <_shifting_type>Duration</_shifting_type>
                </_shifting>
                <_context_data_analysis>
                  <probes/>
                  <ips/>
                </_context_data_analysis>
                <report>
                  <url/>
                </report>
                <_notes>
                  <_notes_general/>
                </_notes>
              </annotations>
              <documentation>
                <input/>
                <output/>
                <implementation>
                  <description/>
                </implementation>
                <code>
                  <description/>
                </code>
              </documentation>
            </call>
            <terminate eid="e2" abandon="true"/>
          </parallel_branch>
        </parallel>
        </description>
    </description>
    <transformation>
        <description type="copy"/>
        <dataelements type="none"/>
        <endpoints type="none"/>
    </transformation>
</testset>
"""


_RECURRING_TEMPLATE = """<testset xmlns="http://cpee.org/ns/properties/2.0">
  <executionhandler>ruby</executionhandler>
  <dataelements/>
  <endpoints>
    <timeout>https-post://cpee.org/services/timeout.php</timeout>
    <subprocess>https-post://cpee.org/flow/start/url/</subprocess>
    <receive>https-get://cpee.org/ing/correlators/message/receive/</receive>
  </endpoints>
  <attributes>
    <guarded>none</guarded>
    <info>Recurring</info>
    <modeltype>CPEE</modeltype>
    <theme>extended</theme>
    <creator>Christine Ashcreek</creator>
    <guarded_id/>
    <author>Christine Ashcreek</author>
    <model_uuid>ba513eb6-1b35-4f87-a7f0-ff4d16828231</model_uuid>
    <model_version/>
    <design_dir>Staff.dir/Loebbi.dir/Voting.dir/Patterns.dir</design_dir>
    <design_stage>development</design_stage>
  </attributes>
  <description>
    <description xmlns="http://cpee.org/ns/description/1.0">
      <parallel eid="e3" wait="-1" cancel="last">
        <parallel_branch>
          <loop eid="e1" mode="pre_test" condition="true">
            <_probability>
              <_probability_min/>
              <_probability_max/>
              <_probability_avg/>
            </_probability>
            <_annotations>
              <_logging_behavior>
                <_iteration>false</_iteration>
              </_logging_behavior>
            </_annotations>
            <call id="a4" endpoint="timeout">
              <parameters>
                <label>Wait</label>
                <color/>
                <arguments>
                  <timeout>20</timeout>
                  <data/>
                </arguments>
              </parameters>
              <code>
                <signal>false</signal>
                <prepare/>
                <finalize output="result"/>
                <update output="result"/>
                <rescue output="result"/>
              </code>
              <annotations>
                <_generic/>
                <_logging_behavior>
                  <_exclude>false</_exclude>
                  <_include>false</_include>
                </_logging_behavior>
                <_timing>
                  <_timing_weight/>
                  <_timing_avg/>
                  <explanations/>
                </_timing>
                <_shifting>
                  <_shifting_type>Duration</_shifting_type>
                </_shifting>
                <_context_data_analysis>
                  <probes/>
                  <ips/>
                </_context_data_analysis>
                <report>
                  <url/>
                </report>
                <_notes>
                  <_notes_general/>
                </_notes>
              </annotations>
              <documentation>
                <input/>
                <output/>
                <implementation>
                  <description/>
                </implementation>
                <code>
                  <description/>
                </code>
              </documentation>
            </call>
            <call id="a1" endpoint="">
              <parameters>
                <label>Task</label>
                <color/>
                <method>:post</method>
                <arguments/>
              </parameters>
              <code>
                <signal>false</signal>
                <prepare/>
                <finalize output="result"/>
                <update output="result"/>
                <rescue output="result"/>
              </code>
              <annotations>
                <_generic/>
                <_logging_behavior>
                  <_exclude>false</_exclude>
                  <_include>false</_include>
                </_logging_behavior>
                <_timing>
                  <_timing_weight/>
                  <_timing_avg/>
                  <explanations/>
                </_timing>
                <_shifting>
                  <_shifting_type>Duration</_shifting_type>
                </_shifting>
                <_context_data_analysis>
                  <probes/>
                  <ips/>
                </_context_data_analysis>
                <report>
                  <url/>
                </report>
                <_notes>
                  <_notes_general/>
                </_notes>
              </annotations>
              <documentation>
                <input/>
                <output/>
                <implementation>
                  <description/>
                </implementation>
                <code>
                  <description/>
                </code>
              </documentation>
            </call>
          </loop>
        </parallel_branch>
        <parallel_branch>
          <call id="a2" endpoint="receive">
            <parameters>
              <label/>
              <color/>
              <arguments>
                <id>__TARGET__</id>
                <ttl>0</ttl>
                <delete>true</delete>
              </arguments>
            </parameters>
            <code>
              <signal>false</signal>
              <prepare/>
              <finalize output="result"/>
              <update output="result"/>
              <rescue output="result"/>
            </code>
            <annotations>
              <_generic/>
              <_logging_behavior>
                <_exclude>false</_exclude>
                <_include>false</_include>
              </_logging_behavior>
              <_timing>
                <_timing_weight/>
                <_timing_avg/>
                <explanations/>
              </_timing>
              <_shifting>
                <_shifting_type>Duration</_shifting_type>
              </_shifting>
              <_context_data_analysis>
                <probes/>
                <ips/>
              </_context_data_analysis>
              <report>
                <url/>
              </report>
              <_notes>
                <_notes_general/>
              </_notes>
            </annotations>
            <documentation>
              <input/>
              <output/>
              <implementation>
                <description/>
              </implementation>
              <code>
                <description/>
              </code>
            </documentation>
          </call>
          <terminate eid="e2" abandon="true"/>
        </parallel_branch>
      </parallel>
    </description>
  </description>
  <transformation>
    <description type="copy"/>
    <dataelements type="none"/>
    <endpoints type="none"/>
  </transformation>
</testset>
"""


_WAIT_FOR_EVENT_TEMPLATE = """<testset xmlns="http://cpee.org/ns/properties/2.0">
    <executionhandler>ruby</executionhandler>
    <dataelements/>
    <endpoints>
        <timeout>https-post://cpee.org/services/timeout.php</timeout>
        <subprocess>https-post://cpee.org/flow/start/url/</subprocess>
        <task>__TASKURL__</task>
    </endpoints>
    <attributes>
        <guarded>none</guarded>
        <info>WaitForEvent</info>
        <modeltype>CPEE</modeltype>
        <theme>extended</theme>
        <creator>Christine Ashcreek</creator>
        <guarded_id/>
        <author>Christine Ashcreek</author>
        <model_uuid>d55cdfcc-7464-4a57-b0e9-3437ca440d6d</model_uuid>
        <model_version/>
        <design_dir>Staff.dir/Loebbi.dir/Voting.dir/Patterns.dir</design_dir>
        <design_stage>development</design_stage>
    </attributes>
    <description>
        <description xmlns="http://cpee.org/ns/description/1.0">
            <call id="a1" endpoint="task">
                <parameters>
                    <label>Task</label>
                    <color/>
                    <method>:post</method>
                    <arguments/>
                </parameters>
                <annotations>
                    <_generic/>
                    <_logging_behavior>
                        <_exclude>false</_exclude>
                        <_include>false</_include>
                    </_logging_behavior>
                    <_timing>
                        <_timing_weight/>
                        <_timing_avg/>
                        <explanations/>
                    </_timing>
                    <_shifting>
                        <_shifting_type>Duration</_shifting_type>
                    </_shifting>
                    <_context_data_analysis>
                        <probes/>
                        <ips/>
                    </_context_data_analysis>
                    <report>
                        <url/>
                    </report>
                    <_notes>
                        <_notes_general/>
                    </_notes>
                </annotations>
                <documentation>
                    <input/>
                    <output/>
                    <implementation>
                        <description/>
                    </implementation>
                </documentation>
            </call>
        </description>
    </description>
    <transformation>
        <description type="copy"/>
        <dataelements type="none"/>
        <endpoints type="none"/>
    </transformation>
</testset>
"""


def _escape_xml_text(value):
        return escape(str(value))


def _escape_xml_attr(value):
        return escape(str(value), _XML_ATTR_ESCAPES)


def MaxExecTime(MaxTime, AlternativeURL, target):
        return (
                _MAX_EXEC_TIME_TEMPLATE
        .replace("__MAX_TIME__", _escape_xml_text(MaxTime))
        .replace("__ALTERNATIVE_URL__", _escape_xml_attr(AlternativeURL))
  .replace("__TARGET__", _escape_xml_attr(target))
        )


def Recurring(CheckURL, TaskURL, Time, target):
        return (
                _RECURRING_TEMPLATE
        .replace("__TASK_URL__", _escape_xml_attr(TaskURL))
        .replace("__TIME__", _escape_xml_text(Time))
  .replace("__TARGET__", _escape_xml_attr(target))
        )


def WaitForEvent(TaskURL):
        return _WAIT_FOR_EVENT_TEMPLATE.replace("__TASKURL__", _escape_xml_attr(TaskURL))